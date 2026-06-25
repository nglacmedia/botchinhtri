from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from datetime import datetime

app = FastAPI(title="Geopolitics & War Online - Sector Lockdown")

@app.get("/", response_class=HTMLResponse)
async def maintenance():
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    return f"""
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TERMINAL - GEOPOLITICS & WAR</title>
        <style>
            :root {{
                --primary: #00ff66;
                --primary-low: rgba(0, 255, 102, 0.2);
                --warn: #ff3333;
                --bg: #050505;
                --panel: rgba(15, 15, 15, 0.9);
                --font: 'Courier New', Courier, monospace;
            }}

            * {{ box-sizing: border-box; }}
            
            body {{
                margin: 0;
                padding: 0;
                background-color: var(--bg);
                color: var(--primary);
                font-family: var(--font);
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                overflow: hidden;
                text-shadow: 0 0 5px var(--primary);
            }}

            /* Hiệu ứng CRT Scanline */
            body::before {{
                content: " ";
                display: block;
                position: fixed;
                top: 0; left: 0; bottom: 0; right: 0;
                background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.1) 50%), 
                            linear-gradient(90deg, rgba(255, 0, 0, 0.03), rgba(0, 255, 0, 0.01), rgba(0, 0, 255, 0.03));
                z-index: 10;
                background-size: 100% 3px, 3px 100%;
                pointer-events: none;
            }}

            /* Hiệu ứng màng quét radar */
            body::after {{
                content: "";
                position: fixed;
                top: -100%; left: 0; width: 100%; height: 100%;
                background: linear-gradient(to bottom, transparent, var(--primary-low), transparent);
                opacity: 0.1;
                animation: scan 8s linear infinite;
                z-index: 11;
                pointer-events: none;
            }}

            .container {{
                width: 95%;
                max-width: 1100px;
                height: 90vh;
                background: var(--panel);
                border: 1px solid var(--primary);
                position: relative;
                display: flex;
                flex-direction: column;
                box-shadow: 0 0 50px rgba(0, 255, 102, 0.1);
                z-index: 5;
            }}

            /* Header Section */
            .top-bar {{
                padding: 10px 20px;
                border-bottom: 1px solid var(--primary);
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: var(--primary-low);
            }}

            .status-tag {{
                background: var(--warn);
                color: white;
                padding: 2px 10px;
                font-weight: bold;
                animation: blink 0.8s infinite;
            }}

            /* Main Layout */
            .main-content {{
                display: grid;
                grid-template-columns: 1fr 350px;
                flex-grow: 1;
                overflow: hidden;
            }}

            .terminal-side {{
                padding: 20px;
                border-right: 1px solid var(--primary-low);
                display: flex;
                flex-grow: 1;
                flex-direction: column;
                overflow-y: auto;
            }}

            .discord-side {{
                padding: 10px;
                background: rgba(0, 0, 0, 0.3);
                display: flex;
                flex-direction: column;
            }}

            /* Components */
            .glitch-title {{
                font-size: 1.8rem;
                font-weight: bold;
                margin: 0 0 10px 0;
                text-transform: uppercase;
                letter-spacing: 5px;
            }}

            .stats-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
                margin-bottom: 20px;
            }}

            .stat-box {{
                border: 1px solid var(--primary-low);
                padding: 10px;
                background: rgba(0, 255, 102, 0.05);
            }}

            .stat-header {{
                font-size: 0.8rem;
                color: #aaa;
                margin-bottom: 5px;
                display: block;
            }}

            .log-window {{
                background: rgba(0, 0, 0, 0.5);
                border: 1px solid var(--primary-low);
                padding: 15px;
                flex-grow: 1;
                font-size: 0.9rem;
                line-height: 1.5;
                margin-bottom: 15px;
                position: relative;
            }}

            .progress-container {{
                margin-top: 10px;
            }}

            .progress-bar {{
                width: 100%;
                height: 4px;
                background: var(--primary-low);
                position: relative;
                overflow: hidden;
            }}

            .progress-fill {{
                position: absolute;
                height: 100%;
                background: var(--primary);
                width: 0%;
                animation: load 4s ease-in-out infinite;
            }}

            .dev-info {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-top: 1px solid var(--primary-low);
                padding-top: 15px;
            }}

            .btn-link {{
                color: var(--bg);
                background: var(--primary);
                padding: 8px 20px;
                text-decoration: none;
                font-weight: bold;
                transition: 0.3s;
                text-transform: uppercase;
                font-size: 0.8rem;
            }}

            .btn-link:hover {{
                box-shadow: 0 0 15px var(--primary);
                transform: scale(1.05);
            }}

            /* Animations */
            @keyframes scan {{
                from {{ top: -100%; }}
                to {{ top: 100%; }}
            }}

            @keyframes blink {{
                0%, 100% {{ opacity: 1; }}
                50% {{ opacity: 0.2; }}
            }}

            @keyframes load {{
                0% {{ width: 0%; }}
                50% {{ width: 80%; }}
                100% {{ width: 100%; }}
            }}

            @media (max-width: 850px) {{
                .main-content {{ grid-template-columns: 1fr; }}
                .discord-side {{ display: none; }}
                .stats-grid {{ grid-template-columns: 1fr; }}
            }}

            ::-webkit-scrollbar {{ width: 5px; }}
            ::-webkit-scrollbar-thumb {{ background: var(--primary); }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="top-bar">
                <div>[ SYSTEM: G&W_CORE_V2 ]</div>
                <div id="clock">{now}</div>
                <div class="status-alert"><span class="status-tag">SYSTEM LOCKDOWN</span></div>
            </div>

            <div class="main-content">
                <div class="terminal-side">
                    <div class="glitch-title">Sector Lockdown</div>
                    <p style="color: #888; margin-bottom: 20px;">>> Khởi chạy giao thức bảo trì Full-Stack. Cơ sở dữ liệu đang được tái cấu trúc toàn diện.</p>
                    
                    <div class="stats-grid">
                        <div class="stat-box">
                            <span class="stat-header">MODULE QUÂN SỰ</span>
                            <div style="color: var(--warn)">● CHẾ ĐỘ ĐÓNG BĂNG</div>
                            <small style="font-size: 0.7rem">Lệnh .taoqg, .xuatbinh đã ngắt kết nối</small>
                        </div>
                        <div class="stat-box">
                            <span class="stat-header">HỆ THỐNG LƯU TRỮ</span>
                            <div>● CLOUD DATABASE</div>
                            <small style="font-size: 0.7rem">Trạng thái: Đang đồng bộ (Synchronizing)</small>
                        </div>
                    </div>

                    <div class="log-window" id="logs">
                        <div style="color: #555;">[SYSTEM LOGS READY]</div>
                        <div>> Đang kết nối tới FastAPI Gateway... OK</div>
                        <div>> Kiểm tra phân đoạn dữ liệu Realtime... OK</div>
                        <div>> Chặn yêu cầu ghi từ người dùng... OK</div>
                        <div id="dynamic-log"></div>
                    </div>

                    <div class="progress-container">
                        <div style="display: flex; justify-content: space-between; font-size: 0.8rem; margin-bottom: 5px;">
                            <span>DEPLOYMENT PROGRESS</span>
                            <span id="percent">87%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill"></div>
                        </div>
                    </div>

                    <div class="dev-info">
                        <div>
                            <span style="display:block; font-size: 0.7rem; color: #888;">CHỦ SỞ HỮU</span>
                            <strong>thehuy_03</strong>
                        </div>
                        <a href="https://discord.gg/7H5d5JX856" target="_blank" class="btn-discord btn-link">GIA NHẬP QUÂN ĐOÀN</a>
                    </div>
                </div>

                <div class="discord-side">
                    <iframe src="https://discord.com/widget?id=1493951797189152891&theme=dark" 
                        width="100%" height="100%" allowtransparency="true" frameborder="0" 
                        sandbox="allow-popups allow-popups-to-escape-sandbox allow-same-origin allow-scripts">
                    </iframe>
                </div>
            </div>

            <div style="font-size: 0.7rem; padding: 5px 20px; border-top: 1px solid var(--primary-low); color: #444;">
                ROOT@GEOPOLITICS-WAR:~$ _ (Waiting for Render deployment...)
            </div>
        </div>

        <script>
            // Cập nhật đồng hồ thời gian thực
            setInterval(() => {{
                const now = new Date();
                document.getElementById('clock').innerText = now.toLocaleDateString() + ' ' + now.toLocaleTimeString();
            }}, 1000);

            // Giả lập log chạy liên tục
            const logs = [
                "> Đang tối ưu hóa PostgreSQL queries...",
                "> Cập nhật Websocket Heartbeat...",
                "> Xử lý tài nguyên biên giới quốc gia...",
                "> Đang nén các tệp tin hệ thống...",
                "> Đang kiểm tra bảo mật API Key..."
            ];
            let i = 0;
            setInterval(() => {{
                const logEl = document.getElementById('dynamic-log');
                logEl.innerHTML += `<div>> ${{logs[i % logs.length]}}</div>`;
                if(logEl.children.length > 4) logEl.removeChild(logEl.firstChild);
                i++;
            }}, 2500);

            // Giả lập phần trăm tiến trình
            setInterval(() => {{
                const p = document.getElementById('percent');
                let val = parseInt(p.innerText);
                if (val < 99) p.innerText = (val + 1) + "%";
            }}, 5000);
        </script>
    </body>
    </html>
    """
