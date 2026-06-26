import discord
from discord.ext import commands

# Cấu hình Intents (Bắt buộc để nhận diện thành viên mới)
intents = discord.Intents.default()
intents.members = True  

bot = commands.Bot(command_prefix="!", intents=intents)

# Thông tin cấu hình
SERVER_NAME = "✧ 𝙄𝙣𝙛𝙞𝙣𝙞𝙩𝙮 𝘾𝙤𝙢𝙢𝙪𝙣𝙞𝙩𝙮 ✧"
BANNER_URL = "https://cdn.discordapp.com/attachments/1496168507371557084/1519929169612378233/ChatGPT_Image_11_55_21_26_thg_6_2026.png?ex=6a3f57d8&is=6a3e0658&hm=6c605291feba86fbd0885d1d5e835e795574d1124753f1cceb15f1c94502cdac&"
# Lưu ý: Link logo bạn gửi là link tin nhắn, bot cần link ảnh trực tiếp (kết thúc bằng .png/.jpg)
# Tôi sẽ tạm để link ảnh đại diện server hoặc bạn hãy thay link ảnh trực tiếp vào đây
LOGO_URL = "https://i.imgur.com/83pZ59S.png" 

@bot.event
async def on_ready():
    print(f'Bot đã sẵn sàng: {bot.user.name}')
    print('------')

@bot.event
async def on_member_join(member):
    # Tìm kênh để gửi tin nhắn chào mừng (thường là kênh hệ thống hoặc bạn điền ID kênh cụ thể)
    channel = member.guild.system_channel 
    
    # Nếu muốn gửi vào 1 kênh nhất định, hãy bỏ comment dòng dưới và điền ID kênh:
    # channel = bot.get_channel(123456789012345678) # Thay ID kênh của bạn vào đây

    if channel is not None:
        embed = discord.Embed(
            title=f"Welcome to {SERVER_NAME}!",
            description=f"Chào mừng {member.mention} đã gia nhập đại gia đình của chúng mình! Chúc bạn có những giây phút vui vẻ tại server.",
            color=discord.Color.blue()
        )
        
        # Ảnh thumbnail (Logo nhỏ bên góc)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        
        # Ảnh Banner lớn bên dưới
        embed.set_image(url=BANNER_URL)
        
        # Footer
        embed.set_footer(text=f"Thành viên thứ {len(member.guild.members)} | {SERVER_NAME}", icon_url=LOGO_URL)

        await channel.send(content=f"Hú hế! Chào mừng {member.mention} nha!", embed=embed)

# Thay 'YOUR_TOKEN_HERE' bằng token con bot của bạn
bot.run('MTUxOTk0NDU1ODM0MTc4NzY4OA.G8dZHj.r_GrA_RScniTIu3CCGBIbsdVPqgSNU_VB2mgTs')
