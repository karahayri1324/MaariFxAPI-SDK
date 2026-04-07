const express = require("express");
const multer = require("multer");
const axios = require("axios");
const fs = require("fs");
const path = require("path");
require("dotenv").config();

const app = express();
app.use(express.json());

const upload = multer({ storage: multer.memoryStorage() });

const MAARIFX_API_KEY = process.env.MAARIFX_API_KEY;
const MAARIFX_BASE_URL =
  process.env.MAARIFX_BASE_URL || "https://api2.ogretimsayfam.com";

if (!MAARIFX_API_KEY) {
  console.error("MAARIFX_API_KEY is not set. Check your .env file.");
  process.exit(1);
}

const DB_PATH = path.join(__dirname, "users.json");

function loadUsers() {
  if (!fs.existsSync(DB_PATH)) return [];
  return JSON.parse(fs.readFileSync(DB_PATH, "utf-8"));
}

function saveUsers(users) {
  fs.writeFileSync(DB_PATH, JSON.stringify(users, null, 2));
}

function findUser(username) {
  const users = loadUsers();
  return users.find((u) => u.username === username);
}

async function maarifxRegisterUser(externalId, displayName, email) {
  const response = await axios.post(
    `${MAARIFX_BASE_URL}/v1/users/register`,
    { external_id: externalId, display_name: displayName, email },
    { headers: { "X-API-Key": MAARIFX_API_KEY, "Content-Type": "application/json" } }
  );
  return response.data;
}

async function maarifxSolve(imageBuffer, filename, options = {}) {
  const FormData = (await import("form-data")).default;
  const form = new FormData();
  form.append("image", imageBuffer, { filename: filename || "image.png" });

  if (options.text) form.append("text", options.text);
  if (options.drawOnImage) form.append("draw_on_image", "true");
  form.append("stream", options.stream === false ? "false" : "true");
  if (options.detailLevel) form.append("detailLevel", String(options.detailLevel));
  if (options.classLevel) form.append("classLevel", options.classLevel);

  const headers = {
    "X-API-Key": MAARIFX_API_KEY,
    ...form.getHeaders(),
  };

  if (options.subUserToken) {
    headers["X-Sub-User-Token"] = options.subUserToken;
  }

  const response = await axios.post(`${MAARIFX_BASE_URL}/v1/solve`, form, {
    headers,
    responseType: options.stream === false ? "json" : "stream",
    timeout: 180000,
  });

  return response;
}

app.post("/register", async (req, res) => {
  try {
    const { username, password, display_name, email } = req.body;

    if (!username || !password) {
      return res.status(400).json({ error: "username and password are required" });
    }

    if (findUser(username)) {
      return res.status(409).json({ error: "Username already exists" });
    }

    let maarifxResult;
    try {
      maarifxResult = await maarifxRegisterUser(
        username,
        display_name || username,
        email
      );
    } catch (err) {
      const status = err.response?.status || 500;
      const message = err.response?.data?.error || err.message || "MaarifX registration error";
      return res.status(status).json({ error: `MaarifX error: ${message}` });
    }

    const users = loadUsers();
    users.push({
      username,
      password,
      display_name: display_name || username,
      email: email || null,
      maarifx_token: maarifxResult.token,
      maarifx_external_id: username,
      created_at: new Date().toISOString(),
    });
    saveUsers(users);

    res.status(201).json({
      message: "Registration successful",
      username,
      daily_limit: maarifxResult.daily_limit,
    });
  } catch (err) {
    console.error("[register] Error:", err.message);
    res.status(500).json({ error: "Server error" });
  }
});

app.post("/solve", upload.single("image"), async (req, res) => {
  try {
    const username = req.headers["x-username"];
    const password = req.headers["x-password"];

    if (!username || !password) {
      return res.status(401).json({ error: "X-Username and X-Password headers required" });
    }

    const user = findUser(username);
    if (!user || user.password !== password) {
      return res.status(401).json({ error: "Invalid credentials" });
    }

    if (!user.maarifx_token) {
      return res.status(500).json({ error: "MaarifX token not found for this user" });
    }

    if (!req.file) {
      return res.status(400).json({ error: "image file is required" });
    }

    const text = req.body.text || "";
    const drawOnImage = req.body.draw_on_image === "true" || req.body.draw_on_image === true;
    const stream = req.body.stream !== "false" && req.body.stream !== false;

    if (stream) {
      const maarifxResponse = await maarifxSolve(
        req.file.buffer,
        req.file.originalname,
        { text, drawOnImage, stream: true, subUserToken: user.maarifx_token }
      );

      res.writeHead(200, {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      });

      maarifxResponse.data.pipe(res);

      req.on("close", () => {
        maarifxResponse.data.destroy();
      });
    } else {
      const maarifxResponse = await maarifxSolve(
        req.file.buffer,
        req.file.originalname,
        { text, drawOnImage, stream: false, subUserToken: user.maarifx_token }
      );

      res.json(maarifxResponse.data);
    }
  } catch (err) {
    const status = err.response?.status || 500;
    const message = err.response?.data?.error || err.message || "Unexpected error";
    console.error("[solve] Error:", message);

    if (!res.headersSent) {
      res.status(status).json({ error: message });
    }
  }
});

app.get("/users", (req, res) => {
  const users = loadUsers().map((u) => ({
    username: u.username,
    display_name: u.display_name,
    email: u.email,
    created_at: u.created_at,
  }));

  res.json({ users, total: users.length });
});

app.get("/usage", async (req, res) => {
  try {
    const response = await axios.get(`${MAARIFX_BASE_URL}/v1/usage`, {
      headers: { "X-API-Key": MAARIFX_API_KEY },
    });
    res.json(response.data);
  } catch (err) {
    const status = err.response?.status || 500;
    const message = err.response?.data?.error || err.message;
    res.status(status).json({ error: message });
  }
});

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log("=".repeat(50));
  console.log("MaarifX Distributor Backend Example");
  console.log("=".repeat(50));
  console.log(`API Key: ${MAARIFX_API_KEY.slice(0, 16)}...`);
  console.log(`Base URL: ${MAARIFX_BASE_URL}`);
  console.log(`Port: ${PORT}`);
  console.log();
  console.log("Endpoints:");
  console.log("  POST /register  - Register new student");
  console.log("  POST /solve     - Solve a question");
  console.log("  GET  /users     - List users");
  console.log("  GET  /usage     - Usage statistics");
  console.log("=".repeat(50));
});
