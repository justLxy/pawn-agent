import asyncio
import httpx

async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Register/Login
        res = await client.post("http://127.0.0.1:8000/api/auth/register", json={"username": "testuser3", "password": "password", "shop_name": "Test Shop"})
        if res.status_code != 200:
            print("Register failed:", res.json())
            res = await client.post("http://127.0.0.1:8000/api/auth/login", json={"username": "testuser3", "password": "password"})
            if res.status_code != 200:
                print("Login failed:", res.json())
                return
        
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get state
        res = await client.get("http://127.0.0.1:8000/api/auth/me", headers=headers)
        state = res.json()["state"]
        
        # Find an item in inventory
        inventory = state.get("inventory", [])
        if not inventory:
            print("No items in inventory")
            return
            
        item_id = inventory[0]["id"]
        print(f"Appraising item {item_id}")
        
        # Appraise
        res = await client.post("http://127.0.0.1:8000/api/appraise_inventory", json={"item_id": item_id, "method": "standard"}, headers=headers)
        print(res.status_code)
        print(res.json())

asyncio.run(main())
