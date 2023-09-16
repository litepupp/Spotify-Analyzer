import axios, { AxiosResponse } from "axios";
import { StreamsPage } from "../models/streams.model";

const BASE_URL = "http://127.0.0.1:5000/api/streams/";

const StreamsService = {
  getStreamsPaginated: (): Promise<AxiosResponse<StreamsPage>> => {
    return axios.get(BASE_URL);
  },
};


export { StreamsService };
