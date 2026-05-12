// =============================
// MESSAGE BOX
// =============================

function showMessage(msg, type="success"){
const box = document.getElementById("msgBox")

box.innerText = msg
box.style.display = "block"

if(type==="error"){
box.style.color="red"
}else{
box.style.color="green"
}

setTimeout(()=>{
box.style.display="none"
},4000)
}


// =============================
// FORM SWITCHING
// =============================

function hideAll(){

document.getElementById("loginForm").style.display="none"
document.getElementById("registerForm").style.display="none"
document.getElementById("forgotForm").style.display="none"
document.getElementById("resetForm").style.display="none"

}

function showLogin(){
hideAll()
document.getElementById("loginForm").style.display="block"
document.getElementById("formTitle").innerText="Login"
}

function showRegister(){
hideAll()
document.getElementById("registerForm").style.display="block"
document.getElementById("formTitle").innerText="Register"
}

function showForgot(){
hideAll()
document.getElementById("forgotForm").style.display="block"
document.getElementById("formTitle").innerText="Forgot Password"
}

function showReset(){
hideAll()
document.getElementById("resetForm").style.display="block"
document.getElementById("formTitle").innerText="Reset Password"
}



// =============================
// LOGIN
// =============================

document.getElementById("loginForm").addEventListener("submit", async function(e){

e.preventDefault()

const email = document.getElementById("email").value
const password = document.getElementById("password").value

const res = await fetch("/auth/login",{
method:"POST",
headers:{
"Content-Type":"application/json"
},
body:JSON.stringify({
identifier: email,
password: password
})
})

const data = await res.json()

if(res.ok){

localStorage.setItem("access_token", data.data.tokens.access_token)
localStorage.setItem("user", JSON.stringify(data.data.user))

showMessage("Login Successful")
this.reset()

setTimeout(()=>{
window.location.href = "/welcome"
}, 800)

}else{

showMessage(data.detail || "Login Failed","error")

}

})



// =============================
// REGISTER
// =============================

document.getElementById("registerForm").addEventListener("submit", async function(e){

e.preventDefault()

const name = document.getElementById("name").value
const email = document.getElementById("reg_email").value
const mobile = document.getElementById("mobile").value
const password = document.getElementById("reg_password").value

const res = await fetch("/auth/register",{
method:"POST",
headers:{
"Content-Type":"application/json"
},
body:JSON.stringify({
full_name:name,
email:email,
mobile:mobile,
password:password
})
})

const data = await res.json()

if(res.ok){

showMessage("Registration Successful")

this.reset()

showLogin()

}else{

showMessage(data.detail || "Registration Failed","error")

}

})



// =============================
// FORGOT PASSWORD
// =============================

document.getElementById("forgotForm").addEventListener("submit", async function(e){

e.preventDefault()

const email = document.getElementById("forgot_email").value

const res = await fetch("/auth/forgot-password",{
method:"POST",
headers:{
"Content-Type":"application/json"
},
body:JSON.stringify({
email:email
})
})

const data = await res.json()

if(res.ok){

showMessage("Reset token generated. Check backend console.")

this.reset()

showReset()

}else{

showMessage(data.detail || "Error","error")

}

})



// =============================
// RESET PASSWORD
// =============================

document.getElementById("resetForm").addEventListener("submit", async function(e){

e.preventDefault()

const token = document.getElementById("reset_token").value
const password = document.getElementById("new_password").value

const res = await fetch("/auth/reset-password",{
method:"POST",
headers:{
"Content-Type":"application/json"
},
body:JSON.stringify({
token:token,
new_password:password
})
})

const data = await res.json()

if(res.ok){

showMessage("Password Reset Successful")

this.reset()

showLogin()

}else{

showMessage(data.detail || "Invalid Token","error")

}

})