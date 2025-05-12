from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import openai
import json

app = FastAPI()

# 提供前端畫面
app.mount("/static", StaticFiles(directory="static"), name="static")


# 讓根目錄回傳 index.html
@app.get("/")
async def get():
    with open("static/index_socket.html", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


# 儲存每個用戶的 API 金鑰和對話紀錄
clients = {}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    client_id = id(websocket)
    clients[client_id] = {"api_key": None, "history": []}

    await websocket.send_json({"type": "info", "message": "連線成功！請先註冊 API 金鑰。"})

    try:
        while True:
            data = await websocket.receive_json()
            client = clients[client_id]

            if data["type"] == "register":
                client["api_key"] = data["api_key"]
                await websocket.send_json({"type": "info", "message": "API 金鑰已註冊完成。"})

            elif data["type"] == "message":
                if not client["api_key"]:
                    await websocket.send_json({"type": "error", "message": "尚未註冊 API 金鑰。"})
                    continue

                user_msg = data["message"]
                print(user_msg)
                client["history"].append({"role": "user", "content": user_msg})

                try:
                    openai.api_key = client["api_key"]
                    print(openai.api_key)
                    openai.base_url = ""
                    openai.default_headers = {"x-foo": "true"}
                    response = openai.chat.completions.create(
                        # model="gpt-3.5-turbo",
                        model="gpt-4o-mini",
                        messages=client["history"]
                    )
                    reply_origin = response.choices[0].message.content
                    reply = reply_origin.split('$~~~$')[-1]
                    print(reply)
                    client["history"].append({"role": "assistant", "content": reply})

                    await websocket.send_json({"type": "reply", "message": reply})
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})

    except WebSocketDisconnect:
        del clients[client_id]
        print(f"Client {client_id} disconnected.")



if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='localhost', port=8000)
