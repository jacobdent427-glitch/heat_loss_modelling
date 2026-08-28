import { useEffect, useState } from "react";

export default function EditableTable({ columns, rows, onUpdate, onDelete, onAdd, newRowDefaults, hideAddRow, hideDeleteColumn, addError }) {
  const [localRows, setLocalRows] = useState(rows);
  const [newRow, setNewRow] = useState(newRowDefaults);

  useEffect(() => {
    setLocalRows(rows);
  }, [rows]);

  const coerce = (col, value) => {
    if (col.type === "number") {
      if (value === "" || value === null || value === undefined) return null;
      const n = parseFloat(value);
      return Number.isNaN(n) ? null : n;
    }
    return value;
  };

  const makeHandlers = (row, col, setRowState) => ({
    onLocalChange: (val) => setRowState((prev) => ({ ...prev, [col.key]: val })),
    onCommit: (val) => {
      if (col.type === "text" || col.type === "number") {
        const fields = { [col.key]: coerce(col, val) };
        setRowState((prev) => ({ ...prev, ...fields }));
        return fields;
      }
      let fields = { [col.key]: coerce(col, val) };
      if (col.onSelect) {
        fields = { ...fields, ...(col.onSelect(val, { ...row, ...fields }) || {}) };
      }
      setRowState((prev) => ({ ...prev, ...fields }));
      return fields;
    },
  });

  const errorStyle = { borderColor: "var(--danger)", borderWidth: "2px", background: "#fdf0ee" };

  const renderInput = (value, col, handlers, immediateCommit, row, hasError) => {
    if (col.type === "readonly") {
      return <span>{col.format ? col.format(value, row) : value}</span>;
    }
    if (col.type === "select") {
      return (
        <select
          value={value ?? ""}
          onChange={(e) => {
            const fields = handlers.onCommit(e.target.value === "" ? null : e.target.value);
            immediateCommit(fields);
          }}
          style={hasError ? errorStyle : undefined}
        >
          <option value="">-</option>
          {col.options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      );
    }
    if (col.type === "checkbox") {
      return (
        <input
          type="checkbox"
          checked={!!value}
          onChange={(e) => immediateCommit(handlers.onCommit(e.target.checked))}
        />
      );
    }
    return (
      <input
        type={col.type === "number" ? "number" : "text"}
        step="any"
        value={value ?? ""}
        onChange={(e) => handlers.onLocalChange(e.target.value)}
        onBlur={(e) => immediateCommit(handlers.onCommit(e.target.value))}
        style={{ ...(col.width ? { width: col.width } : undefined), ...(hasError ? errorStyle : undefined) }}
        title={hasError || undefined}
      />
    );
  };

  return (
    <table className="editable-table">
      <thead>
        <tr>
          {columns.map((c) => (
            <th key={c.key}>{c.label}</th>
          ))}
          {!hideDeleteColumn && <th></th>}
        </tr>
      </thead>
      <tbody>
        {localRows.map((row) => (
          <tr key={row.id}>
            {columns.map((c) => {
              const setRowState = (updater) =>
                setLocalRows((prev) => prev.map((r) => (r.id === row.id ? updater(r) : r)));
              const handlers = makeHandlers(row, c, setRowState);
              return (
                <td key={c.key}>
                  {renderInput(row[c.key], c, handlers, (fields) => onUpdate(row.id, fields).catch(() => {}), row)}
                </td>
              );
            })}
            {!hideDeleteColumn && (
              <td>
                <button className="danger" onClick={() => onDelete(row.id)}>
                  Delete
                </button>
              </td>
            )}
          </tr>
        ))}
        {localRows.length === 0 && (
          <tr>
            <td colSpan={columns.length + (hideDeleteColumn ? 0 : 1)} className="muted">
              No rows yet.
            </td>
          </tr>
        )}
      </tbody>
      {!hideAddRow && (
        <tfoot>
          <tr>
            {columns.map((c) => {
              const handlers = makeHandlers(newRow, c, setNewRow);
              const fieldError = addError?.fieldErrors?.[c.key];
              return <td key={c.key}>{renderInput(newRow[c.key], c, handlers, () => {}, newRow, fieldError)}</td>;
            })}
            <td>
              <button
                onClick={async () => {
                  try {
                    await onAdd(newRow);
                    setNewRow(newRowDefaults);
                  } catch {
                    // keep what was typed so it isn't lost - the error is shown near this button
                  }
                }}
              >
                Add
              </button>
            </td>
          </tr>
        </tfoot>
      )}
    </table>
  );
}
