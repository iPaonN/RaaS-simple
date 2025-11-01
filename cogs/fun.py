"""
Fun Commands
"""
import discord
from discord import app_commands
from discord.ext import commands
import random
from utils.embeds import create_info_embed


class Fun(commands.Cog):
    """Fun and entertainment commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="roll", description="Roll a dice")
    @app_commands.describe(sides="Number of sides on the dice (default: 6)")
    async def roll(
        self,
        interaction: discord.Interaction,
        sides: int = 6
    ):
        """Roll a dice with specified number of sides"""
        if sides < 2:
            await interaction.response.send_message("❌ Dice must have at least 2 sides!", ephemeral=True)
            return
        
        result = random.randint(1, sides)
        embed = create_info_embed(
            title="🎲 Dice Roll",
            description=f"You rolled a **{result}** (1-{sides})"
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="coinflip", description="Flip a coin")
    async def coinflip(self, interaction: discord.Interaction):
        """Flip a coin"""
        result = random.choice(["Heads", "Tails"])
        emoji = "🪙" if result == "Heads" else "🎯"
        embed = create_info_embed(
            title=f"{emoji} Coin Flip",
            description=f"The coin landed on **{result}**!"
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="8ball", description="Ask the magic 8-ball a question")
    @app_commands.describe(question="Your yes/no question")
    async def eightball(
        self,
        interaction: discord.Interaction,
        question: str
    ):
        """Magic 8-ball responses"""
        responses = [
            "It is certain.", "It is decidedly so.", "Without a doubt.",
            "Yes definitely.", "You may rely on it.", "As I see it, yes.",
            "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
            "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
            "Cannot predict now.", "Concentrate and ask again.",
            "Don't count on it.", "My reply is no.", "My sources say no.",
            "Outlook not so good.", "Very doubtful."
        ]
        
        response = random.choice(responses)
        embed = create_info_embed(
            title="🎱 Magic 8-Ball",
            description=f"**Question:** {question}\n**Answer:** {response}"
        )
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="choose", description="Choose between multiple options")
    @app_commands.describe(options="Options separated by commas (e.g., pizza, pasta, burger)")
    async def choose(
        self,
        interaction: discord.Interaction,
        options: str
    ):
        """Choose randomly from provided options"""
        choices = [opt.strip() for opt in options.split(',') if opt.strip()]
        
        if len(choices) < 2:
            await interaction.response.send_message(
                "❌ Please provide at least 2 options separated by commas!",
                ephemeral=True
            )
            return
        
        choice = random.choice(choices)
        embed = create_info_embed(
            title="🎯 Random Choice",
            description=f"I choose: **{choice}**"
        )
        embed.add_field(
            name="Options",
            value=", ".join(choices),
            inline=False
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    """Load the cog"""
    await bot.add_cog(Fun(bot))
