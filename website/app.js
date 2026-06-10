/*const express = require("express");
const app = express();

app.get("/", (req, res) => {
    res.send("Portal Application Running");
});

app.listen(3000, () => {
    console.log("Server running on port 3000");
});*/

const express = require("express");
const path = require("path");

const app = express();

app.use(express.static(path.join(__dirname, "public")));

// main route
app.get("/websitename", (req, res) => {
    res.sendFile(path.join(__dirname, "public", "index.html"));
});

app.listen(3000, "0.0.0.0", () => {
    console.log("Webapp1 running on port 3000");
});