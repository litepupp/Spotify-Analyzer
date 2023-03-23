export interface Streams {
  id: number;
  track_id: number;
  album_id: number;
  stream_date: Date;
  ms_played: number;
  ratio_played: number;
  reason_start: string;
  reason_end: string;
  shuffle: boolean;
  created_date: Date;
  modified_date: Date;
}

export interface StreamsPage {
  page: number;
  per_page: number;
  items: Streams[];
  total: number;
}
