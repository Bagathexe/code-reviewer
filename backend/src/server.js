import express from "express";
import dotenv from "dotenv";

dotenv.config();

const app=express();

app.use(express.json());

app.get("/health",(req,res)=>{
    res.status(200).json({message:"success"});
})

app.listen(process.env.PORT,()=>{
    console.log(`Server running on PORT :: ${process.env.PORT}`);
})