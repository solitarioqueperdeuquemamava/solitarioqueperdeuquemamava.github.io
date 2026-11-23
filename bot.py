import asyncio
import os
import re
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")

# Cargos superiores com acesso ao ticket e permissão para fechar
CARGO_DONO_ID = 1574232963552509963
CARGO_SUB_DONO_ID = 1574232985228673166
CARGOS_SUPERIORES_IDS = {CARGO_DONO_ID, CARGO_SUB_DONO_ID}

# URL do GIF do painel
GIF_URL = "https://pictureurl.com/api/storage/file?key=u%2Fanon%2Fd7caa3ac-81ee-46fa-9fe6-89d529a83284-1000011367.gif[span_1](start_span)"[span_1](end_span)

# Opcional: coloque sua chave PIX aqui se quiser que apareça dentro do ticket
CHAVE_PIX = ""

PRODUTO = {
    "titulo": "KAZUMI HUB — SOURCE DINO HUB",
    "subtitulo": "⚡ Entrega via Ticket / Atendimento",
    "itens": [
        "SOURCE DINO HUB COMPLETA",
        "PAINEL E ESTRUTURA ORGANIZADA",
        "SUPORTE NO TICKET APÓS COMPRA",
        "ATUALIZAÇÕES DO KAZUMI HUB"
    ],
    "valor": "R$ 3,50",
    "pagamento": "PIX",
    "restam": "∞"
}

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)


def membro_e_superior(member: discord.abc.User) -> bool:
    if not isinstance(member, discord.Member):
        return False
    if member.guild_permissions.administrator:
        return True
    return any(role.id in CARGOS_SUPERIORES_IDS for role in member.roles)


def montar_embed(guild: discord.Guild) -> discord.Embed:
    descricao = (
        f"**{PRODUTO['subtitulo']}**\n\n"
        + "\n\n".join(PRODUTO["itens"])
        + f"\n\n**Valor à vista**\n`{PRODUTO['valor']}`\n\n"
        + f"**Pagamento**\n`{PRODUTO['pagamento']}`\n\n"
        + f"**Restam**\n`{PRODUTO['restam']}`"
    )

    embed = discord.Embed(
        description=descricao,
        color=discord.Color.from_rgb(124, 58, 237)
    )

    icon_url = guild.icon.url if guild.icon else (bot.user.display_avatar.url if bot.user else None)
    if icon_url:
        embed.set_author(name=PRODUTO["titulo"], icon_url=icon_url)
        embed.set_footer(text="Kazumi Hub • Pagamento via PIX", icon_url=icon_url)
    else:
        embed.set_author(name=PRODUTO["titulo"])
        embed.set_footer(text="Kazumi Hub • Pagamento via PIX")

    if GIF_URL:
        embed.set_image(url=GIF_URL)

    return embed


class ControleTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Fechar Ticket",
        style=discord.ButtonStyle.red,
        emoji="🔒",
        custom_id="kazumi_fechar_ticket"
    )
    async def fechar_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not membro_e_superior(interaction.user):
            await interaction.response.send_message(
                "❌ Apenas **Dono**, **Sub dono** ou **Administradores** podem fechar este ticket.",
                ephemeral=True
            )
            return

        canal = interaction.channel
        if not isinstance(canal, discord.TextChannel):
            await interaction.response.send_message("Este botão só funciona em canal de texto.", ephemeral=True)
            return

        await interaction.response.send_message("🔒 Fechando ticket em 3 segundos...")
        await asyncio.sleep(3)

        try:
            await canal.delete(reason=f"Ticket fechado por {interaction.user}")
        except discord.Forbidden:
            await canal.send("❌ Não tenho permissão para apagar este canal.")


class ComprarDinoHubView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Comprar Source Dino Hub",
        style=discord.ButtonStyle.green,
        emoji="🛒",
        custom_id="kazumi_comprar_dino_hub"
    )
    async def comprar_dino_hub(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        if not guild:
            await interaction.response.send_message("Use este botão dentro de um servidor.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        nome_limpo = re.sub(r"[^a-z0-9-]", "", user.name.lower().replace(" ", "-"))[:15] or "cliente"
        prefixo_canal = f"ticket-dino-{nome_limpo}"

        canal_existente = discord.utils.find(
            lambda c: isinstance(c, discord.TextChannel) and c.name.startswith(prefixo_canal),
            guild.text_channels
        )
        if canal_existente:
            await interaction.followup.send(
                f"Você já tem um ticket aberto: {canal_existente.mention}",
                ephemeral=True
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                read_message_history=True
            )
        }

        mencoes_superiores = []
        for cargo_id in CARGOS_SUPERIORES_IDS:
            cargo = guild.get_role(cargo_id)
            if cargo:
                overwrites[cargo] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_channels=True
                )
                mencoes_superiores.append(cargo.mention)

        try:
            canal_ticket = await guild.create_text_channel(
                name=f"{prefixo_canal}-{str(user.id)[-4:]}",
                overwrites=overwrites,
                reason=f"Ticket de compra Source Dino Hub por {user}"
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Não consegui criar o canal do ticket. Verifique se o Kazumi Bot tem permissão de **Gerenciar Canais**.",
                ephemeral=True
            )
            return
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao abrir o ticket: `{e}`", ephemeral=True)
            return

        texto_pix = f"\n**Chave PIX:** `{CHAVE_PIX}`" if CHAVE_PIX else "\nAguarde o envio da chave PIX pela equipe."

        ticket_embed = discord.Embed(
            title="🎫 Ticket Aberto — Kazumi Hub",
            description=(
                f"Olá {user.mention}! Seu ticket para comprar a **Source Dino Hub** foi aberto.\n\n"
                f"**Produto:** Source Dino Hub\n"
                f"**Valor à vista:** `{PRODUTO['valor']}`\n"
                f"**Forma de pagamento:** `{PRODUTO['pagamento']}`"
                f"{texto_pix}"
            ),
            color=discord.Color.from_rgb(124, 58, 237)
        )

        mencoes = " ".join([user.mention] + mencoes_superiores)
        await canal_ticket.send(content=mencoes, embed=ticket_embed, view=ControleTicketView())

        await interaction.followup.send(
            f"✅ Ticket criado! Clique aqui para ir direto ao ticket: {canal_ticket.mention}",
            ephemeral=True
        )


@bot.event
async def on_ready():
    bot.add_view(ComprarDinoHubView())
    bot.add_view(ControleTicketView())
    print(f"Kazumi Hub online como {bot.user} (ID: {bot.user.id})")


@bot.command(name="painel")
async def painel(ctx: commands.Context):
    if not ctx.guild:
        return
    embed = montar_embed(ctx.guild)
    await ctx.send(embed=embed, view=ComprarDinoHubView())


if not TOKEN:
    raise RuntimeError("A variável de ambiente DISCORD_TOKEN não foi definida.")

bot.run(TOKEN)
