import { PrismaClient } from "@prisma/client";
import express from "express";

const app = express();
const port = 3000;

const prisma = new PrismaClient();

app.get("/", (req, res) => {
  prisma.artist
    .findMany()
    .then((artist) => {
      res.json(artist);
    })
    .finally(() => {});
});

app.listen(port, () => {
  console.log(`listening on PORT:${port}`);
});
