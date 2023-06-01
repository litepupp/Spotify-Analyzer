import express from "express";

const app = express();
const port = 3000;

app.get("/", (req, res) => {
  res.send("OOF");
});

app.listen(port, () => {
  console.log(`listening on PORT:${port}`);
});
