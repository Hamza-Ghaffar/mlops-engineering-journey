const mongoose = require("mongoose");
const dotenv = require("dotenv");

dotenv.config();

async function connectDB() {
  try {
    await mongoose.connect(process.env.MONGO_URI);

    console.log("MongoDB connected successfully");
  } catch (error) {
    console.error("Error connecting to MongoDB:", error);
  }
}

module.exports = connectDB;
