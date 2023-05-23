import { useState, useEffect, useMemo } from "react";
import { AgGridReact } from "ag-grid-react";
import { AxiosResponse } from "axios";

import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-alpine.css";
import { Streams, StreamsPage } from "./models/streams.model";
import { StreamsService } from "./services/streams.service";
import { ValueFormatterParams } from "ag-grid-community";

const App = () => {
  const [streamData, setStreamData] = useState<Streams[]>([]);
  const [totalTime, setTotalTime] = useState<number>(0);

  const [columnDefs] = useState([
    { headerName: "Stream ID", field: "id", filter: "agNumberColumnFilter" },
    {
      headerName: "Track ID",
      field: "track_id",
      filter: "agNumberColumnFilter",
    },
    {
      headerName: "Album ID",
      field: "album_id",
      filter: "agNumberColumnFilter",
    },
    {
      headerName: "Date Streamed",
      field: "stream_date",
      filter: "agDateColumnFilter",
      valueFormatter: (params: ValueFormatterParams<Streams, Date>) =>
        params.value.toLocaleDateString("ja-JP", {
          year: "numeric",
          month: "long",
          day: "numeric",
          weekday: "long",
          hour: "2-digit",
          minute: "2-digit",
        }),
    },
    {
      headerName: "Time played (ms)",
      field: "ms_played",
      filter: "agNumberColumnFilter",
    },
    {
      headerName: "Completion rate",
      field: "ratio_played",
      filter: "agNumberColumnFilter",
    },
    {
      headerName: "Starting Reason",
      field: "reason_start",
      filter: "agTextColumnFilter",
    },
    {
      headerName: "Ending Reason",
      field: "reason_end",
      filter: "agTextColumnFilter",
    },
    {
      headerName: "Was Shuffled",
      field: "shuffle",
      filter: "agTextColumnFilter",
    },
  ]);

  const defaultColDef = useMemo(
    () => ({
      sortable: true,
      resizable: true,
    }),
    []
  );

  useEffect(() => {
    StreamsService.getStreamsPaginated().then(
      ({ data }: AxiosResponse<StreamsPage>) => {
        setTotalTime(
          data.items.reduce((acc: number, { ms_played }) => acc + ms_played, 0)
        );
        setStreamData(
          data.items.map(
            ({ stream_date, created_date, modified_date, ...stream }) => ({
              ...stream,
              stream_date: new Date(stream_date + "Z"),
              created_date: new Date(created_date + "Z"),
              modified_date: new Date(modified_date + "Z"),
            })
          )
        );
      }
    );
  }, []);

  return (
    <div>
      <div className="ag-theme-alpine" style={{ width: 1000, height: 600 }}>
        <div>Total ms_played = {totalTime}</div>
        <AgGridReact
          rowData={streamData}
          columnDefs={columnDefs}
          animateRows={true}
          defaultColDef={defaultColDef}
          rowSelection="multiple"
        />
      </div>
    </div>
  );
};

export default App;
