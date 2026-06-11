const express = require("express");
const path = require("path");

const app = express();

// Lets express read JSON from frontend
app.use(express.json());
app.use(express.urlencoded({ extended: true}))

// Serve static frontend files
app.use(express.static(path.join(__dirname, "public")));

// main route
app.get("/websitename", (req, res) => {
    res.sendFile(path.join(__dirname, "public", "index.html"));
});

app.post("/websitename/contact-submit", (req, res) =>{
    const {name, email, message} = req.body;

    res.send({message: "Form received successfully!"});
})

app.listen(3000, "0.0.0.0", () => {
    console.log("Webapp1 running on port 3000");
});