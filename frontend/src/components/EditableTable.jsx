import { useEffect, useState } from "react";

/**
 * Generic spreadsheet-like editable table.
 *
 * columns: [{ key, label, type: 'text'|'number'|'checkbox'|'select'|'readonly', options?, width?,
 *              onSelect?: (value, row) => extraFieldsObject, format?: (value, row) => displayValue }]
 *   `onSelect` lets a select column (e.g. an age-band picker) derive/pre-fill other fields
 *   (e.g. the U-value) in the same row when it changes - the result is merged into both the
 *   local row state and the update sent to the server.
 * rows: array of row objects (must include `id`)
 * onUpdate(id, partialFields), onDelete(id), onAdd(newRowFields)
 * newRowDefaults: object of default values for the add-row form
 * hideAddRow / hideDeleteColumn: hide the add-new-row form / per-row delete button, for tables
 *   that edit fields on existing rows only (e.g. the fabric-improvements view over elements
 *   already created elsewhere).
 */
export default function EditableTable({ columns, rows, onUpdate, onDelete, onAdd, newRowDefaults, hideAddRow, hideDeleteColumn }) {
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

  // Handles select/checkbox changes (commit immediately) and text/number local edits.
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

  const renderInput = (value, col, handlers, immediateCommit, row) => {
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
                <td key={c.key}>{renderInput(row[c.key], c, handlers, (fields) => onUpdate(row.id, fields), row)}</td>
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
              return <td key={c.key}>{renderInput(newRow[c.key], c, handlers, () => {}, newRow)}</td>;
            })}
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
      )}
    </table>
  );
}
