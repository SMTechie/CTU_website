const express = require("express");
const path = require("path");
const pool = require("./db");

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

app.post("/contact-submit", async (req, res) =>{
    try{
        const {name, email, message} = req.body;

    const result = await pool.query(
        `INSERT INTO tickets (name, email, message, status)
        VALUES ($1, $2, $3, $4)
        RETURNING id`,
        [name, email, message, "New"]
    );

    const ticketId = result.rows[0].id;

    await fetch("http://webapp2:8080/email/ticket-created", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            name: name,
            email: email,
            subject: message
        })
    });

    res.json({
        message: "Form received successfully"
    });

    }catch(err){
        console.log(err);
        res.status(500).json({message: "Error submitting ticket"});
    }
    
})

app.listen(3000, "0.0.0.0", () => {
    console.log("Webapp1 running on port 3000");
});