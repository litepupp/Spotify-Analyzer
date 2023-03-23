import React, { useState, useEffect, useMemo } from "react";
import { AgGridReact } from "ag-grid-react";
import axios from "axios";

import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";

const App = () => {
  const [rowData, setRowData] = useState();

  const [columnDefs, setColumnDefs] = useState([
    { headerName: "Stream ID", field: "id", filter: "agNumberColumnFilter" },
    { field: "track_id", filter: "agNumberColumnFilter" },
    { field: "album_id", filter: "agNumberColumnFilter" },
    { field: "stream_date", filter: "agDateColumnFilter" },
    { field: "ms_played", filter: "agNumberColumnFilter" },
    { field: "ratio_played", filter: "agNumberColumnFilter" },
    { field: "reason_start", filter: "agTextColumnFilter" },
    { field: "reason_end", filter: "agTextColumnFilter" },
    { field: "shuffle", filter: "agTextColumnFilter" },
  ]);

  const defaultColDef = useMemo(
    () => ({
      sortable: true,
      resizable: true,
    }),
    []
  );

  useEffect(() => {
    axios.get("http://127.0.0.1:5000/api/streams/").then((response) => {
      setRowData(response.data.items);
    });
  }, []);

  return (
    <div>
      <div className="ag-theme-alpine" style={{ width: 1000, height: 600 }}>
        <AgGridReact
          rowData={rowData} // Row Data for Rows
          columnDefs={columnDefs} // Column Defs for Columns
          animateRows={true} // Optional - set to 'true' to have rows animate when sorted
          defaultColDef={defaultColDef}
          rowSelection="multiple" // Options - allows click selection of rows
        />
      </div>
    </div>
  );
};

export default App;
