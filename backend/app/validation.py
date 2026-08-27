from flask import jsonify


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def validate(data, strict_positive=(), positive_if_set=(), non_negative_if_set=(), fraction_if_set=(), range_if_set=None):
    errors = {}

    for f in strict_positive:
        if f in data:
            v = _num(data[f])
            if v is None or v <= 0:
                errors[f] = "must be a number greater than 0"

    for f in positive_if_set:
        if f in data and data[f] is not None:
            v = _num(data[f])
            if v is None or v <= 0:
                errors[f] = "must be a number greater than 0"

    for f in non_negative_if_set:
        if f in data and data[f] is not None:
            v = _num(data[f])
            if v is None or v < 0:
                errors[f] = "cannot be negative"

    for f in fraction_if_set:
        if f in data and data[f] is not None:
            v = _num(data[f])
            if v is None or v < 0 or v > 1:
                errors[f] = "must be between 0 and 1"

    if range_if_set:
        for f, lo, hi in range_if_set:
            if f in data and data[f] is not None:
                v = _num(data[f])
                if v is None or v < lo or v > hi:
                    errors[f] = f"must be between {lo} and {hi}"

    return errors


def error_response(errors):
    message = "; ".join(f"{field}: {msg}" for field, msg in errors.items())
    return jsonify({"error": message, "errors": errors}), 400
