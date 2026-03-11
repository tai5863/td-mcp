"""
TouchDesigner WebServer DAT Callbacks — TD Bridge for td-mcp

Setup:
1. Create a WebServer DAT in TouchDesigner
2. Set Port to 9980
3. Paste this entire file into the WebServer DAT's callbacks
4. Toggle the WebServer DAT's Active parameter ON

Compatible with TouchDesigner 2023.12230+
"""

import json
import traceback
import base64
import fnmatch

# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

def _ok(response, data=None):
    """Send a success response."""
    body = json.dumps({"ok": True, "data": data or {}})
    response["statusCode"] = 200
    response["statusReason"] = "OK"
    response["data"] = body


def _err(response, msg, code="INTERNAL", status=400, **extra):
    """Send an error response. Extra kwargs are merged into the payload."""
    payload = {"ok": False, "error": msg, "code": code}
    payload.update(extra)
    body = json.dumps(payload)
    response["statusCode"] = status
    response["statusReason"] = "Error"
    response["data"] = body


def _resolve_op(path):
    """Resolve a TD operator by path. Returns (op, error_string)."""
    target = op(path)
    if target is None:
        return None, f"Operator not found: {path}"
    return target, None


# Family suffixes used by TouchDesigner op type class names
_FAMILIES = ("CHOP", "TOP", "SOP", "DAT", "COMP", "MAT")


def _fuzzy_op_types(query, max_results=5):
    """Return op type class names that fuzzy-match *query*.

    Searches the td module for names containing the query (case-insensitive).
    Falls back to suffix-aware matching and prefix matching for typos.
    """
    import td as _td
    # Collect only real op type names (skip bare family base classes like "CHOP")
    all_op_types = []
    for name in dir(_td):
        for f in _FAMILIES:
            if name.endswith(f) and len(name) > len(f):
                all_op_types.append(name)
                break

    q_lower = query.lower()

    # Pass 1: substring match on full name
    candidates = [n for n in all_op_types if q_lower in n.lower()]

    if not candidates:
        # Strip family suffix from query for base-name matching
        q_base = q_lower
        q_family = ""
        for f in _FAMILIES:
            if q_lower.endswith(f.lower()):
                q_base = q_lower[:-len(f)]
                q_family = f
                break

        for name in all_op_types:
            n_lower = name.lower()
            # Strip family suffix from candidate
            n_base = n_lower
            for f in _FAMILIES:
                if n_lower.endswith(f.lower()):
                    n_base = n_lower[:-len(f)]
                    break
            # Skip if families don't match (when query specifies one)
            if q_family and not n_lower.endswith(q_family.lower()):
                continue
            if q_base in n_base or n_base in q_base:
                candidates.append(name)

    if not candidates and len(q_lower) >= 3:
        # Pass 3: prefix match (first 3+ chars) for typos like noize→noise
        q_base = q_lower
        q_family = ""
        for f in _FAMILIES:
            if q_lower.endswith(f.lower()):
                q_base = q_lower[:-len(f)]
                q_family = f
                break
        prefix_len = max(3, len(q_base) // 2)
        prefix = q_base[:prefix_len]
        for name in all_op_types:
            n_lower = name.lower()
            if q_family and not n_lower.endswith(q_family.lower()):
                continue
            n_base = n_lower
            for f in _FAMILIES:
                if n_lower.endswith(f.lower()):
                    n_base = n_lower[:-len(f)]
                    break
            if n_base.startswith(prefix):
                candidates.append(name)

    # Deduplicate and sort by similarity (shorter length distance = better)
    seen = set()
    unique = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            unique.append(c)
    unique.sort(key=lambda n: abs(len(n) - len(query)))
    return unique[:max_results]


# ---------------------------------------------------------------------------
# Field extraction
# ---------------------------------------------------------------------------

DEFAULT_FIELDS = ["name", "type", "family"]

def _op_fields(o, fields=None):
    """Extract requested fields from an operator."""
    fields = fields or DEFAULT_FIELDS
    result = {}
    for f in fields:
        if f == "name":
            result["name"] = o.name
        elif f == "type":
            result["type"] = o.OPType
        elif f == "family":
            result["family"] = o.family
        elif f == "path":
            result["path"] = o.path
        elif f == "inputs":
            result["inputs"] = [i.path for i in o.inputs]
        elif f == "outputs":
            result["outputs"] = [c.path for c in o.outputs]
        elif f == "numChildren":
            result["numChildren"] = len(o.children)
        elif f == "comment":
            result["comment"] = o.comment
        elif f == "storage":
            result["storage"] = str(dict(o.storage))
        elif f == "tags":
            result["tags"] = list(o.tags)
        elif f == "nodeX":
            result["nodeX"] = o.nodeX
        elif f == "nodeY":
            result["nodeY"] = o.nodeY
    return result


# ---------------------------------------------------------------------------
# Action handlers
# ---------------------------------------------------------------------------

def _handle_create_op(params):
    parent_path = params["parent"]
    op_type_name = params["op_type"]
    name = params.get("name")
    init_params = params.get("params", {})

    parent_op, err = _resolve_op(parent_path)
    if err:
        return {"error": err, "code": "OP_NOT_FOUND"}

    # Resolve op type class (e.g. "noiseCHOP" -> noiseCHOP)
    try:
        op_class = eval(op_type_name)
    except Exception:
        # Fuzzy match: suggest similar op type names
        suggestions = _fuzzy_op_types(op_type_name)
        result = {"error": f"Invalid op type: {op_type_name}", "code": "INVALID_OP_TYPE"}
        if suggestions:
            result["suggestions"] = suggestions
        return result

    new_op = parent_op.create(op_class, name or "")

    # Set position if provided
    node_x = params.get("nodeX")
    node_y = params.get("nodeY")
    if node_x is not None:
        new_op.nodeX = node_x
    if node_y is not None:
        new_op.nodeY = node_y

    # Apply initial params
    for k, v in init_params.items():
        try:
            setattr(new_op.par, k, v)
        except Exception:
            pass  # skip invalid params silently during creation

    result = {"path": new_op.path, "name": new_op.name, "type": new_op.OPType,
              "nodeX": new_op.nodeX, "nodeY": new_op.nodeY}

    # GLSL TOP: include auto-generated DAT paths so the caller
    # doesn't create redundant textDATs
    if new_op.OPType in ("glslmultiTOP", "glslTOP"):
        auto_dats = {}
        for attr in ("pixeldat", "vertexdat", "outputdat", "computedat"):
            try:
                p = getattr(new_op.par, attr, None)
                if p is not None:
                    dat_op = p.eval()
                    if dat_op and hasattr(dat_op, "path"):
                        auto_dats[attr] = dat_op.path
            except Exception:
                pass
        if auto_dats:
            result["auto_dats"] = auto_dats

    return {"data": result}


def _handle_delete_op(params):
    path = params["path"]
    target, err = _resolve_op(path)
    if err:
        return {"error": err, "code": "OP_NOT_FOUND"}
    name = target.name
    target.destroy()
    return {"data": {"deleted": path, "name": name}}


def _handle_list_ops(params):
    path = params["path"]
    parent_op, err = _resolve_op(path)
    if err:
        return {"error": err, "code": "OP_NOT_FOUND"}

    family = params.get("family")
    type_filter = params.get("type_filter")
    fields = params.get("fields")
    limit = params.get("limit", 50)
    offset = params.get("offset", 0)

    children = parent_op.children
    if family:
        children = [c for c in children if c.family == family]
    if type_filter:
        children = [c for c in children if c.OPType == type_filter]

    total = len(children)
    page = children[offset:offset + limit]
    items = [_op_fields(c, fields) for c in page]

    return {"data": {"items": items, "total": total, "offset": offset, "limit": limit}}


def _handle_get_op_info(params):
    path = params["path"]
    target, err = _resolve_op(path)
    if err:
        return {"error": err, "code": "OP_NOT_FOUND"}
    fields = params.get("fields")
    return {"data": _op_fields(target, fields)}


def _handle_set_params(params):
    path = params["path"]
    par_dict = params["params"]

    target, err = _resolve_op(path)
    if err:
        return {"error": err, "code": "OP_NOT_FOUND"}

    set_ok = []
    errors = []
    for k, v in par_dict.items():
        try:
            setattr(target.par, k, v)
            set_ok.append(k)
        except Exception as e:
            errors.append({"param": k, "error": str(e)})

    result = {"set": set_ok}
    if errors:
        result["errors"] = errors
    return {"data": result}


def _handle_get_params(params):
    path = params["path"]
    names = params.get("names")
    pattern = params.get("pattern")
    discover = params.get("discover", False)
    page = params.get("page", 0)
    page_size = 50

    target, err = _resolve_op(path)
    if err:
        return {"error": err, "code": "OP_NOT_FOUND"}

    if names:
        # Specific params requested — return all, including defaults
        result = {}
        for n in names:
            try:
                p = getattr(target.par, n)
                result[n] = p.eval()
            except Exception:
                result[n] = None
        return {"data": {"params": result, "total": len(result)}}

    # Gather params with optional pattern filter
    all_pars = target.pars()
    if pattern:
        all_pars = [p for p in all_pars if fnmatch.fnmatch(p.name, pattern)]
    elif not discover:
        # Non-default only for token efficiency
        all_pars = [p for p in all_pars if not p.isDefault]

    total = len(all_pars)
    paged = all_pars[page * page_size:(page + 1) * page_size]

    result = {}
    for p in paged:
        try:
            if discover:
                # Rich schema: name, value, default, type, range, page
                val = p.eval()
                defval = p.default
                # Ensure JSON-serializable values
                if not isinstance(val, (int, float, str, bool, type(None))):
                    val = str(val)
                if not isinstance(defval, (int, float, str, bool, type(None))):
                    defval = str(defval)
                entry = {
                    "value": val,
                    "default": defval,
                    "type": p.mode.name if hasattr(p, "mode") else str(type(p.eval()).__name__),
                    "page": p.page.name if hasattr(p, "page") else "",
                }
                # Include range if numeric
                try:
                    if hasattr(p, "normMin"):
                        entry["min"] = p.normMin
                    if hasattr(p, "normMax"):
                        entry["max"] = p.normMax
                except Exception:
                    pass
                # Include menu items if it's a menu parameter
                try:
                    if hasattr(p, "menuNames") and p.menuNames:
                        entry["menuNames"] = list(p.menuNames)
                        entry["menuLabels"] = list(p.menuLabels)
                except Exception:
                    pass
                result[p.name] = entry
            else:
                result[p.name] = p.eval()
        except Exception:
            result[p.name] = str(p)

    return {"data": {"params": result, "total": total, "page": page, "pageSize": page_size}}


def _handle_connect(params):
    from_path = params["from_op"]
    to_path = params["to_op"]
    from_idx = params.get("from_index", 0)
    to_idx = params.get("to_index", 0)

    from_op, err = _resolve_op(from_path)
    if err:
        return {"error": err, "code": "OP_NOT_FOUND"}

    to_op, err = _resolve_op(to_path)
    if err:
        return {"error": err, "code": "OP_NOT_FOUND"}

    try:
        to_op.inputConnectors[to_idx].connect(from_op.outputConnectors[from_idx])
    except Exception as e:
        return {"error": f"Connection failed: {e}", "code": "CONNECT_FAIL"}

    return {"data": {"from": from_path, "to": to_path, "fromIndex": from_idx, "toIndex": to_idx}}


def _handle_disconnect(params):
    path = params["path"]
    connector = params.get("connector", "input")
    index = params.get("index", 0)

    target, err = _resolve_op(path)
    if err:
        return {"error": err, "code": "OP_NOT_FOUND"}

    try:
        if connector == "input":
            target.inputConnectors[index].disconnect()
        else:
            target.outputConnectors[index].disconnect()
    except Exception as e:
        return {"error": f"Disconnect failed: {e}", "code": "CONNECT_FAIL"}

    return {"data": {"path": path, "connector": connector, "index": index}}


def _handle_execute(params):
    code = params["code"]
    return_expr = params.get("return_expression")

    local_ns = {}
    try:
        exec(code, {"op": op, "me": me}, local_ns)
    except Exception:
        tb = traceback.format_exc().splitlines()[-5:]
        return {"error": "\n".join(tb), "code": "EXEC_ERROR"}

    result = {"executed": True}
    if return_expr:
        try:
            result["result"] = eval(return_expr, {"op": op, "me": me, **local_ns})
        except Exception as e:
            result["result"] = None
            result["evalError"] = str(e)

    return {"data": result}


def _handle_find_empty_space(params):
    parent_path = params["parent"]
    width = params.get("width", 200)
    height = params.get("height", 200)
    direction = params.get("direction", "right")  # right, below, grid
    padding = params.get("padding", 50)

    parent_op, err = _resolve_op(parent_path)
    if err:
        return {"error": err, "code": "OP_NOT_FOUND"}

    children = parent_op.children
    if not children:
        return {"data": {"nodeX": 0, "nodeY": 0}}

    # Collect bounding boxes of existing ops: (x, y, x+w, y+h)
    # nodeWidth/nodeHeight are in network editor units
    boxes = []
    for c in children:
        cx = c.nodeX
        cy = c.nodeY
        cw = c.nodeWidth if hasattr(c, "nodeWidth") else 200
        ch = c.nodeHeight if hasattr(c, "nodeHeight") else 200
        boxes.append((cx, cy, cx + cw, cy + ch))

    if direction == "right":
        # Find rightmost edge, place after it
        max_right = max(b[2] for b in boxes)
        return {"data": {"nodeX": max_right + padding, "nodeY": boxes[0][1]}}

    elif direction == "below":
        # Find bottommost edge, place below it
        max_bottom = max(b[3] for b in boxes)
        return {"data": {"nodeX": boxes[0][0], "nodeY": max_bottom + padding}}

    else:
        # Grid layout: scan for first non-overlapping slot
        # Start from top-left of existing bounding area and scan right, then down
        min_x = min(b[0] for b in boxes)
        min_y = min(b[1] for b in boxes)

        def _overlaps(nx, ny):
            """Check if a rect at (nx, ny, nx+width, ny+height) overlaps any box."""
            for bx1, by1, bx2, by2 in boxes:
                if nx < bx2 + padding and nx + width > bx1 - padding and \
                   ny < by2 + padding and ny + height > by1 - padding:
                    return True
            return False

        # Scan in a grid pattern
        step = padding + max(width, height)
        for row in range(50):
            for col in range(50):
                test_x = min_x + col * step
                test_y = min_y + row * step
                if not _overlaps(test_x, test_y):
                    return {"data": {"nodeX": test_x, "nodeY": test_y}}

        # Fallback: place far right
        max_right = max(b[2] for b in boxes)
        return {"data": {"nodeX": max_right + padding, "nodeY": min_y}}


def _handle_get_screenshot(params):
    path = params["path"]
    width = params.get("width", 640)
    fmt = params.get("format", "jpeg")

    target, err = _resolve_op(path)
    if err:
        return {"error": err, "code": "OP_NOT_FOUND"}

    if target.family != "TOP":
        return {"error": f"{path} is not a TOP (family={target.family})", "code": "NOT_A_TOP"}

    try:
        orig_w = target.width
        orig_h = target.height

        # TD 2023 saveByteArray: (filetype, quality=1.0) — no width/height
        if fmt == "png":
            img_bytes = target.saveByteArray(".png")
            mime = "image/png"
        else:
            img_bytes = target.saveByteArray(".jpg", quality=0.7)
            mime = "image/jpeg"

        b64 = base64.b64encode(img_bytes).decode("ascii")
        return {"data": {"image": b64, "mime": mime, "width": orig_w, "height": orig_h}}
    except Exception:
        tb = traceback.format_exc().splitlines()[-5:]
        return {"error": "\n".join(tb), "code": "INTERNAL"}


# ---------------------------------------------------------------------------
# Action router
# ---------------------------------------------------------------------------

HANDLERS = {
    "create_op": _handle_create_op,
    "delete_op": _handle_delete_op,
    "list_ops": _handle_list_ops,
    "get_op_info": _handle_get_op_info,
    "set_params": _handle_set_params,
    "get_params": _handle_get_params,
    "connect": _handle_connect,
    "disconnect": _handle_disconnect,
    "execute": _handle_execute,
    "get_screenshot": _handle_get_screenshot,
    "find_empty_space": _handle_find_empty_space,
}


# ---------------------------------------------------------------------------
# WebServer DAT callback
# ---------------------------------------------------------------------------

def onHTTPRequest(webServerDAT, request, response):
    """Main entry point — called by TouchDesigner's WebServer DAT."""
    # Only handle POST /api
    method = request.get("method", "GET")
    uri = request.get("uri", "")

    if method != "POST" or uri != "/api":
        _err(response, f"Not found: {method} {uri}", code="NOT_FOUND", status=404)
        return response

    # Parse JSON body
    try:
        body = json.loads(request.get("data", "{}"))
    except json.JSONDecodeError as e:
        _err(response, f"Invalid JSON: {e}", code="INVALID_JSON")
        return response

    action = body.get("action")
    if not action or action not in HANDLERS:
        _err(response, f"Unknown action: {action}", code="UNKNOWN_ACTION")
        return response

    params = body.get("params", {})

    # Dispatch
    try:
        result = HANDLERS[action](params)
    except Exception:
        tb = traceback.format_exc().splitlines()[-5:]
        _err(response, "\n".join(tb), code="INTERNAL", status=500)
        return response

    # Handler returns {"data": ...} on success or {"error": ..., "code": ...} on failure
    if "error" in result:
        extra = {}
        if "suggestions" in result:
            extra["suggestions"] = result["suggestions"]
        _err(response, result["error"], code=result.get("code", "INTERNAL"), **extra)
    else:
        _ok(response, result.get("data"))

    return response
