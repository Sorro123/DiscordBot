import discord
from discord import app_commands
from discord.ext import commands
import io
import os
import imageio_ffmpeg # type: ignore
import scripts.functions as functions
functions.reload(functions)

FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
ffmpeg_options = {
    'before_options': '-f s16le -ar 24000 -ac 1',
    'options': '-vn',
}

class Voice(commands.Cog):
    def __init__(self, client):
        self.client = client

    @app_commands.command(name="join", description="Joins the voice channel you are currently in.")
    async def join(self, interaction: discord.Interaction):
        if interaction.user.voice is None:
            await interaction.response.send_message("You are not in a voice channel.", ephemeral=True)
            return

        voice_channel = interaction.user.voice.channel
        if interaction.guild.voice_client is None:
            # Bot is not in any voice channel in this guild
            try:
                await voice_channel.connect()
                await interaction.response.send_message(f"Joined {voice_channel.mention}!", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"Could not join {voice_channel.mention}: {e}", ephemeral=True)
        else:
            # Bot is already in a voice channel in this guild
            if interaction.guild.voice_client.channel == voice_channel:
                await interaction.response.send_message(f"I am already in {voice_channel.mention}.", ephemeral=True)
            else:
                try:
                    await interaction.guild.voice_client.move_to(voice_channel)
                    await interaction.response.send_message(f"Moved to {voice_channel.mention}!", ephemeral=True)
                except Exception as e:
                    await interaction.response.send_message(f"Could not move to {voice_channel.mention}: {e}", ephemeral=True)

    @app_commands.command(name="leave", description="Leaves the voice channel the bot is currently in.")
    async def leave(self, interaction: discord.Interaction):
        if interaction.guild.voice_client is None or not interaction.guild.voice_client.is_connected():
            await interaction.response.send_message("I am not in any voice channel.", ephemeral=True)
            return

        current_channel = interaction.guild.voice_client.channel
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message(f"Left {current_channel.mention}.", ephemeral=True)

    @app_commands.command(name="tts", description="AI-based text to speech.")
    async def tts(self, interaction: discord.Interaction, message: str):
        if(interaction.guild.voice_client.channel is not interaction.user.voice.channel):
            await interaction.response.send_message("I am not in the same voice channel as you, or you are not in a voice channel.", ephemeral=True)
        else:
            await interaction.response.defer(thinking=True, ephemeral=True)
            try:
                data = await functions.generate_audio(message, functions.get_voice_prompt(interaction.user.id))
                audio_buffer = io.BytesIO(data)
                audio_buffer.seek(0)
                interaction.guild.voice_client.play(discord.FFmpegPCMAudio(audio_buffer, executable=FFMPEG_PATH, pipe=True, **ffmpeg_options), after=lambda e: print(f'Player error: {e}') if e else None)
            except Exception as e:
                await interaction.edit_original_response(content=f"Error: {e}")
                return
            await interaction.guild.voice_client.channel.send(f"<@{interaction.user.id}>: {message}")
            await interaction.edit_original_response(content="TTS complete.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None:
            return
        if message.author.bot:
            return
        
        if message.content.startswith("~"):
            if(message.guild.voice_client is None):
                await message.reply("I am not in any voice channel.", delete_after=5)
                return
            
            if(message.channel is not message.guild.voice_client.channel):
                await message.reply("This feature must be used in the voice channel side chat the bot is in.", delete_after=5)
                return
            
            if(not message.author.voice or message.author.voice.channel is not message.guild.voice_client.channel):
                await message.reply("You are not in the voice channel.", delete_after=5)
                return

            if message.content.startswith("~ "):
                message.content = message.content[2:]
            else:
                message.content = message.content[1:]
            
            try:
                data = await functions.generate_audio(message.content, functions.get_voice_prompt(message.author.id))
                audio_buffer = io.BytesIO(data)
                audio_buffer.seek(0)
                message.guild.voice_client.play(discord.FFmpegPCMAudio(audio_buffer, executable=FFMPEG_PATH, pipe=True, **ffmpeg_options), after=lambda e: message.reply(f"Player error: {e}", delete_after=10) if e else None)
            except Exception as e:
                await message.reply(f"Error: {e}", delete_after=10)
                return
            await message.reply(content="TTS complete.", delete_after=5)

async def setup(client):
    await client.add_cog(Voice(client))