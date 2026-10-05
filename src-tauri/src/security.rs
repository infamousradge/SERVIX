use argon2::{password_hash::{rand_core::OsRng, PasswordHash, PasswordHasher, PasswordVerifier, SaltString}, Argon2};
pub fn hash_password(password:&str)->Result<String,String>{
 if password.len()<8 { return Err("Password must be at least 8 characters.".into()); }
 let salt=SaltString::generate(&mut OsRng);
 Argon2::default().hash_password(password.as_bytes(),&salt).map(|x|x.to_string()).map_err(|e|format!("Password hashing failed: {e}"))
}
pub fn verify_password(password:&str,hash:&str)->bool{
 PasswordHash::new(hash).ok().map(|parsed|Argon2::default().verify_password(password.as_bytes(),&parsed).is_ok()).unwrap_or(false)
}
