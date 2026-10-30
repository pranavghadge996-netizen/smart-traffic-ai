const express = require("express");
const cors = require("cors");
const bcrypt = require("bcryptjs");
const jwt = require("jsonwebtoken");
const fs = require("fs");
const path = require("path");
require("dotenv").config();

const app = express();

const PORT = 5000;
const JWT_SECRET = process.env.JWT_SECRET || "smart-traffic-secret-key";

app.use(cors());
app.use(express.json());

// ------------------------------------
// USERS FILE
// ------------------------------------

const usersFile = path.join(__dirname, "users.json");

if (!fs.existsSync(usersFile)) {
  fs.writeFileSync(usersFile, "[]");
}

function getUsers() {
  try {
    const data = fs.readFileSync(usersFile, "utf8");
    return JSON.parse(data);
  } catch (error) {
    return [];
  }
}

function saveUsers(users) {
  fs.writeFileSync(
    usersFile,
    JSON.stringify(users, null, 2)
  );
}

// ------------------------------------
// TEST ROUTE
// ------------------------------------

app.get("/", (req, res) => {
  res.json({
    message: "Smart Traffic AI Backend is running",
  });
});

// ------------------------------------
// REGISTER
// ------------------------------------

app.post("/api/register", async (req, res) => {
  try {
    const {
      name,
      email,
      password,
      role,
    } = req.body;

    if (!name || !email || !password) {
      return res.status(400).json({
        message: "Name, email and password are required.",
      });
    }

    const users = getUsers();

    const existingUser = users.find(
      (user) =>
        user.email.toLowerCase() === email.toLowerCase()
    );

    if (existingUser) {
      return res.status(409).json({
        message: "An account with this email already exists.",
      });
    }

    const hashedPassword = await bcrypt.hash(
      password,
      10
    );

    const newUser = {
      id: Date.now().toString(),
      name,
      email: email.toLowerCase(),
      password: hashedPassword,
      role: role || "official",
      createdAt: new Date().toISOString(),
    };

    users.push(newUser);

    saveUsers(users);

    const token = jwt.sign(
      {
        id: newUser.id,
        email: newUser.email,
        role: newUser.role,
      },
      JWT_SECRET,
      {
        expiresIn: "7d",
      }
    );

    res.status(201).json({
      message: "Account created successfully.",
      token,
      user: {
        id: newUser.id,
        name: newUser.name,
        email: newUser.email,
        role: newUser.role,
      },
    });

  } catch (error) {
    console.error("REGISTER ERROR:", error);

    res.status(500).json({
      message: "Registration failed.",
    });
  }
});

// ------------------------------------
// LOGIN
// ------------------------------------

app.post("/api/login", async (req, res) => {
  try {
    const {
      email,
      password,
    } = req.body;

    if (!email || !password) {
      return res.status(400).json({
        message: "Email and password are required.",
      });
    }

    const users = getUsers();

    const user = users.find(
      (item) =>
        item.email.toLowerCase() === email.toLowerCase()
    );

    if (!user) {
      return res.status(401).json({
        message: "Invalid email or password.",
      });
    }

    const passwordCorrect = await bcrypt.compare(
      password,
      user.password
    );

    if (!passwordCorrect) {
      return res.status(401).json({
        message: "Invalid email or password.",
      });
    }

    const token = jwt.sign(
      {
        id: user.id,
        email: user.email,
        role: user.role,
      },
      JWT_SECRET,
      {
        expiresIn: "7d",
      }
    );

    res.json({
      message: "Login successful.",
      token,
      user: {
        id: user.id,
        name: user.name,
        email: user.email,
        role: user.role,
      },
    });

  } catch (error) {
    console.error("LOGIN ERROR:", error);

    res.status(500).json({
      message: "Login failed.",
    });
  }
});

// ------------------------------------
// START SERVER
// ------------------------------------

app.listen(PORT, () => {
  console.log(
    `Smart Traffic backend running on http://localhost:${PORT}`
  );
});