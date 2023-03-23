import axios, { AxiosResponse } from "axios";
import { StreamsPage } from "../models/streams.model";

export const getStreamsPaginated = (): Promise<AxiosResponse<StreamsPage>> => {
  return axios.get("http://127.0.0.1:5000/api/streams/");
};
