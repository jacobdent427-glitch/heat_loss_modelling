import { useEffect, useState } from "react";

/**
 * Generic spreadsheet-like editable table.
 *
 * columns: [{ key, label, type: 'text'|'number'|'checkbox'|'select', options?, width? }]
 * rows: array of row objects (must include `id`)
 * onUpdate(id, partialFields)
 * onDelete(id)
 * onAdd(newRowFields) -> called with the "new row" form values
 * newRowDefaults: object of default values for the add-row form
 */
export default function EditableTable({ columns, rows, onUpdate, onDelete, onAdd, newRowDefaults }) {
  const [localRows, setLocalRows] = useState(rows);
  const [newRow, setNewRow] = useState(newRowDefaults);

  useEffect(() => {
    setLocalRows(rows);
  }, [rows]);

  const setCell = (id, key, value) => {
    setLocalRows((prev) => prev.map((r) => (r.id === id ? { ...r, [key]: value } : r)));
  };

  const coerce = (col, value) => {
    if (col.type === "number") {
      if (value === "" || value === null || value === undefined) return null;
      const n = parseFloat(value);
      return Number.isNaN(n) ? null : n;
    }
    return value;
  };

  const commitCell = (id, col) => {
    const row = localRows.find((r) => r.id === id);
    onUpdate(id, { [col.key]: coerce(col, row[col.key]) });
  };

  const renderInput = (value, col, onLocalChange, onCommit) => {
    if (col.type === "readonly") {
      return <span>{col.format ? col.format(value) : value}</span>;
    }
    if (col.type === "select") {
      return (
        <select value={value ?? ""} onChange={(e) => onCommit(e.target.value === "" ? null : e.target.value)}>
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
      return <input type="checkbox" checked={!!value} onChange={(e) => onCommit(e.target.checked)} />;
    }
    return (
      <input
        type={col.type === "number" ? "number" : "text"}
        step="any"
        value={value ?? ""}
        onChange={(e) => onLocalChange(e.target.value)}
        onBlur={() => onCommit(value)}
        style={col.width ? { width: col.width } : undefined}
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
          <th></th>
        </tr>
      </thead>
      <tbody>
        {localRows.map((row) => (
          <tr key={row.id}>
            {columns.map((c) => (
              <td key={c.key}>
                {renderInput(
                  row[c.key],
                  c,
                  (val) => setCell(row.id, c.key, val),
                  (val) => {
                    if (c.type !== "text" && c.type !== "number") {
                      setCell(row.id, c.key, val);
                      onUpdate(row.id, { [c.key]: coerce(c, val) });
                    } else {
                      commitCell(row.id, c);
                    }
                  }
                )}
              </td>
            ))}
            <td>
              <button className="danger" onClick={() => onDelete(row.id)}>
                Delete
              </button>
            </td>
          </tr>
        ))}
      </tbody>
      <tfoot>
        <tr>
          {columns.map((c) => (
            <td key={c.key}>
              {renderInput(
                newRow[c.key],
                c,
                (val) => setNewRow((prev) => ({ ...prev, [c.key]: val })),
                (val) => setNewRow((prev) => ({ ...prev, [c.key]: val }))
              )}
            </td>
          ))}
          <td>
            <button
              onClick={() => {
                onAdd(newRow);
                setNewRow(newRowDefaults);
              }}
            >
              Add
            </button>
          </td>
        </tr>
      </tfoot>
    </table>
  );
}
