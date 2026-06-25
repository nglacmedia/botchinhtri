from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="Geopolitics & War Online - Sector Lockdown")

@app.get("/", response_class=HTMLResponse)
async def maintenance():
    return """
    <!DOCTYPE html>
    <html lang="vi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>HỆ THỐNG ĐÓNG BĂNG - GEOPOLITICS & WAR</title>
        <style>
            :root {
                --primary: #00ff66;
                --bg: #0a0a0a;
                --panel: #121212;
                --warn: #ff3333;
                --link: #00bfff;
            }
            body {
                margin: 0;
                padding: 0;
                background-color: var(--bg);
                color: var(--primary);
                font-family: 'Courier New', Courier, monospace;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                overflow-x: hidden;
                padding: 20px 0;
                box-sizing: border-box;
            }
            body::before {
                content: " ";
                display: block;
                position: absolute;
                top: 0; left: 0; bottom: 0; right: 0;
                background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06));
                z-index: 2;
                background-size: 100% 2px, 3px 100%;
                pointer-events: none;
            }
            .terminal {
                width: 90%;
                max-width: 800px;
                background: var(--panel);
                border: 2px solid var(--primary);
                box-shadow: 0 0 30px rgba(0, 255, 102, 0.15);
                padding: 30px;
                position: relative;
                box-sizing: border-box;
            }
            .header {
                border-bottom: 2px dashed var(--primary);
                padding-bottom: 15px;
                margin-bottom: 20px;
                text-align: center;
            }
            .header h1 {
                margin: 0;
                font-size: 24px;
                letter-spacing: 3px;
                text-transform: uppercase;
                animation: blink 1.5s infinite;
            }
            .status-alert {
                color: var(--warn);
                border: 1px solid var(--warn);
                padding: 10px;
                display: inline-block;
                margin-top: 10px;
                font-weight: bold;
                background: rgba(255, 51, 51, 0.1);
                animation: pulse 2s infinite;
            }
            .grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-top: 20px;
            }
            @media (max-width: 768px) {
                .grid { grid-template-columns: 1fr; }
            }
            .panel-box {
                border: 1px solid rgba(0, 255, 102, 0.3);
                padding: 15px;
                background: rgba(0, 0, 0, 0.4);
            }
            .panel-title {
                font-weight: bold;
                border-bottom: 1px solid rgba(0, 255, 102, 0.3);
                padding-bottom: 5px;
                margin-bottom: 10px;
                color: #fff;
            }
            .loading-bar {
                width: 100%;
                height: 12px;
                border: 1px solid var(--primary);
                margin-top: 15px;
                position: relative;
                overflow: hidden;
            }
            .loading-fill {
                height: 100%;
                background: var(--primary);
                width: 45%;
                animation: progress 4s infinite linear;
            }
            .log-text {
                font-size: 13px;
                color: rgba(0, 255, 102, 0.7);
                line-height: 1.6;
            }
            .layout-main {
                display: grid;
                grid-template-columns: 1fr 350px;
                gap: 20px;
                margin-top: 20px;
            }
            @media (max-width: 768px) {
                .layout-main { grid-template-columns: 1fr; }
                .discord-widget { display: flex; justify-content: center; }
            }
            .contact-zone {
                margin-top: 20px;
                border: 1px dashed var(--primary);
                padding: 15px;
                text-align: center;
                background: rgba(0, 255, 102, 0.05);
            }
            .btn-discord {
                display: inline-block;
                margin-top: 10px;
                padding: 8px 16px;
                border: 1px solid var(--link);
                color: var(--link);
                text-decoration: none;
                font-weight: bold;
                transition: all 0.3s;
            }
            .btn-discord:hover {
                background: var(--link);
                color: #000;
                box-shadow: 0 0 10px var(--link);
            }
            @keyframes blink {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.4; }
            }
            @keyframes pulse {
                0%, 100% { box-shadow: 0 0 5px rgba(255, 51, 51, 0.2); }
                50% { box-shadow: 0 0 15px rgba(255, 51, 51, 0.6); }
            }
            @keyframes progress {
                0% { width: 0%; }
                50% { width: 70%; }
                100% { width: 100%; }
            }
        </style>
    </head>
    <body>
        <div class="terminal">
            <div class="header">
                <h1>HỆ THỐNG QUÂN SỰ TOÀN CẦU</h1>
                <div class="status-alert">MÃ LỆNH: BẢO TRÌ DIỆN RỘNG</div>
            </div>
            
            <p style="text-align: center; font-size: 15px; margin: 0;">
                Cơ sở dữ liệu trung tâm đang thực hiện đồng bộ cấu trúc Full-Stack.
                Mọi hoạt động điều binh, ngân sách và liên minh tạm thời đóng băng để nâng cấp.
            </p>

            <div class="layout-main">
                <div>
                    <div class="grid">
                        <div class="panel-box">
                            <div class="panel-title">> TRẠNG THÁI QUỐC GIA</div>
                            <div class="log-text">
                                • Lệnh .taoqg: TẠM KHÓA<br>
                                • Lệnh .xuatbinh: ĐÓNG BĂNG<br>
                                • Ngân sách: AN TOÀN
                            </div>
                        </div>
                        <div class="panel-box">
                            <div class="panel-title">> CẤU TRÚC</div>
                            <div class="log-text">
                                • Backend: FastAPI<br>
                                • DB: PostgreSQL<br>
                                • WS: Realtime
                            </div>
                        </div>
                    </div>

                    <div class="contact-zone">
                        <div class="log-text">⚡ **DEVELOPER:** thehuy_03</div>
                        <a href="https://discord.gg/7H5d5JX856" target="_blank" class="btn-discord">CỘNG ĐỒNG DISCORD</a>
                    </div>

                    <div style="margin-top: 20px;">
                        <div class="loading-bar">
                            <div class="loading-fill"></div>
                        </div>
                    </div>
                </div>

                <div class="discord-widget">
                    <iframe src="https://discord.com/widget?id=1493951797189152891&theme=dark" width="350" height="400" allowtransparency="true" frameborder="0" sandbox="allow-popups allow-popups-to-escape-sandbox allow-same-origin allow-scripts"></iframe>
                </div>
            </div>
            
            <p style="text-align: center; font-size: 11px; margin-top: 25px; margin-bottom: 0; color: rgba(0,255,102,0.4);">
                Hệ thống tự động vận hành lại sau khi hoàn tất chỉ thị deploy trên Render.
            </p>
        </div>
    </body>
    </html>
    """
