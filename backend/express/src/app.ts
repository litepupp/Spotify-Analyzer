import { PrismaClient, Stream } from "@prisma/client";
import express from "express";

const app = express();
const port = 3000;

const prisma = new PrismaClient();

app.get("/", (req, res) => {
  prisma.stream
    .findMany()
    .then((streams) => {
      res.json(streams);
    })
    .finally(() => {});
});

app.listen(port, () => {
  console.log(`listening on PORT:${port}`);
});
