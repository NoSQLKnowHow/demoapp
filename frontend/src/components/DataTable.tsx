import { ReactNode } from "react";

export type TableColumn<T> = {
  key: string;
  header: string;
  render: (item: T) => ReactNode;
  className?: string;
};

type DataTableProps<T> = {
  data: T[] | undefined;
  columns: TableColumn<T>[];
  emptyMessage?: string;
  onRowClick?: (item: T) => void;
  getRowKey?: (item: T, index: number) => string | number;
  getRowClassName?: (item: T, index: number) => string;
};

function DataTable<T>({
  data,
  columns,
  emptyMessage = "No records found.",
  onRowClick,
  getRowKey,
  getRowClassName,
}: DataTableProps<T>) {
  if (!data || data.length === 0) {
    return <p className="text-sm text-slate-400">{emptyMessage}</p>;
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/50">
      <table className="min-w-full divide-y divide-slate-800 text-sm">
        <thead className="bg-slate-900/80 text-slate-300">
          <tr>
            {columns.map((column) => (
              <th key={column.key} scope="col" className={`px-4 py-3 text-left font-medium ${column.className ?? ""}`}>
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800 text-slate-100">
          {data.map((item, rowIndex) => (
            <tr
              key={getRowKey ? getRowKey(item, rowIndex) : rowIndex}
              className={`hover:bg-slate-900/60 ${onRowClick ? "cursor-pointer" : ""} ${
                getRowClassName ? getRowClassName(item, rowIndex) : ""
              }`}
              onClick={() => {
                if (onRowClick) {
                  onRowClick(item);
                }
              }}
            >
              {columns.map((column) => (
                <td key={column.key} className={`px-4 py-3 align-top text-slate-200 ${column.className ?? ""}`}>
                  {column.render(item)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default DataTable;
