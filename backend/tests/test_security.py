from auth.security import hash_password, verify_password

def test_hash_password_produces_different_hash_each_time():
    hash1 = hash_password("hunter123")
    hash2 = hash_password("hunter123")
    assert hash1 != hash2
    
def test_verify_password_correct():
    hashed = hash_password("helloworld")
    assert verify_password("helloworld", hashed) is True
    
def test_verify_password_incorrect():
    hashed = hash_password("NeverChangeUnlessYouWantTo")
    assert verify_password("randomCrap", hashed) is False


    