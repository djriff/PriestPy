from dict import DictionaryReader
from botkey import Key
from discord import utils
from discord import Embed
from discord import Colour
from discord import ActivityType
from twitchHandler import TwitchHandler

class RoleHandler:

    async def newsSubscriptionAdd(client, emoji, user_id, guild_id):

        if not emoji.is_custom_emoji():
            return

        targetRole = '{0}News'.format(emoji.name.capitalize())        

        print(targetRole)
        guild = client.get_guild(guild_id)
        role = utils.find(lambda r: r.name == targetRole, guild.roles)

        if not role:
            return

        member = guild.get_member(user_id)        
        p = DictionaryReader()

        if role not in member.roles:
            await member.add_roles(role, reason='Subscribed to {0}'.format(targetRole))
            await member.send(p.readEntry('newssubscriptionadd', '').format(targetRole))

    async def newsSubscriptionRemove(client, emoji, user_id, guild_id):


        if not emoji.is_custom_emoji():
            return

        targetRole = '{0}News'.format(emoji.name.capitalize())        

        print(targetRole)
        guild = client.get_guild(guild_id)
        role = utils.find(lambda r: r.name == targetRole, guild.roles)

        if not role:
            return

        member = guild.get_member(user_id) 
        p = DictionaryReader()         

        if role in member.roles:
            await member.remove_roles(role, reason='Unsubscribed to {0}'.format(targetRole))
            await member.send(p.readEntry('newssubscriptionremove', '').format(targetRole))

    async def newsSubscription(client, message):
        p = DictionaryReader()

        if not message.guild:
            return

        targetRole = '{0}News'.format(message.content[5::].capitalize())

        print(targetRole)

        role = utils.find(lambda r: r.name == targetRole, message.author.guild.roles)

        # Role Desired doesn't exist
        if not role:
            await message.author.send('Invalid subscription name. Valid subscriptions are:\n{0}'.format(p.readEntry('validsubscriptions','')))            
        else:
            # Doesn't have the role already
            if role not in message.author.roles:
                await message.author.add_roles(role, reason='Subscribed to {0}'.format(targetRole))
                await message.author.send(p.readEntry('newssubscriptionadd', '').format(targetRole))

            # Already has the role, unsubscribing
            else:  
                await message.author.remove_roles(role, reason='Unsubscribed to {0}'.format(targetRole))
                await message.author.send(p.readEntry('newssubscriptionremove', '').format(targetRole))
    
    async def toggleStream(client, message):
        p = DictionaryReader()

        print(message.content)
        
        target = message.mentions[0] if message.mentions else message.author
        
        role  = utils.find(lambda r: r.name == p.streamingRole(), target.roles)
        staff = utils.find(lambda r: r.name == p.roles(), message.author.roles)
        donor = utils.find(lambda r: r.name == p.donor(), message.author.roles)
        streamingRole = utils.find(lambda r: r.name == p.streamingRole(), message.author.guild.roles)
                
        # Target doesn't have the Streaming Role
        if role is None:
                    
            # If user has the Staff role
            if staff is not None:
                await target.add_roles(streamingRole, reason='Role added by {0.name}'.format(message.author))
                
            else:
            # Donors can add the role to themselves
                if donor is not None:
                    await message.author.add_roles(streamingRole, reason='Donor adding role to themselves')
        
        # User already has the Streaming Role, so remove it
        else:
            # If user has the Staff role or is the author
            if staff is not None or target == message.author:
                await target.remove_roles(role, reason='Role removed by {0.name}'.format(message.author))

    async def toggleUserState(client, before, after):
        p = DictionaryReader()
        
        streamingRole = utils.find(lambda r: r.name == p.streamingRole(), before.guild.roles)     
                 
        # User doesn't have the streaming role, move along
        if streamingRole not in before.roles:
            return
        
        # Left the server
        if after is None:
            await RoleHandler.removeStream(client, before)
        # Role was removed        
        elif streamingRole in before.roles and streamingRole not in after.roles:
            print('role removed')
            await RoleHandler.removeStream(client, before)
        
        # Checks if the Game state changed or if the user isn't streaming
        # This or statement might be costly and subject to improvement
        elif before.activity != after.activity or after.activity is None or after.activity.type != ActivityType.streaming:
            
            # Fetches streaming activities in after and before to compare, to avoid reposting
            beforeStream = None
            stream = None
            for act in after.activities:
                if act.type == ActivityType.streaming:
                    stream = act
                    break

            for act in before.activities:
                if act.type == ActivityType.streaming:
                    beforeStream = act
                    break

            if after.activity is None or not stream:
                # Stopped Streaming                
                await RoleHandler.removeStream(client, after)                
                    
            elif stream and beforeStream != stream:
                # Started Streaming
                await RoleHandler.addStream(client, after)
        
        
    async def removeStream(client, member):
        p = DictionaryReader()
        channel = client.get_channel(int(p.streamingBroadcastChannel()))
        currentlyStreaming = utils.find(lambda r: r.name == p.currentlyStreamingRole(), member.guild.roles)
                        
        if channel is None:
            print('Streaming Channel not found!')
            return
            
        await member.remove_roles(currentlyStreaming, reason='User stopped streaming')
        
        # This could be slow, but shouldn't, assuming there should be few messages in the channel
        messages = await channel.history(limit=None).flatten()
        
        for message in messages:
            if member in message.mentions:
                await message.delete()
    
    async def addStream(client, member):
        p = DictionaryReader()
        channel = client.get_channel(int(p.streamingBroadcastChannel()))
        currentlyStreaming = utils.find(lambda r: r.name == p.currentlyStreamingRole(), member.guild.roles)
        
        await RoleHandler.removeStream(client, member)

        stream = None
        for act in member.activities:
            if act.type == ActivityType.streaming:
                stream = act
                        
        if channel is None:
            print('Streaming Channel not found!')
            return
        
        #if not await TwitchHandler.validateStream(stream.url, Key().twitchApiKey()):
           # return
        if not stream.game.startswith('World of Warcraft'):
            return
        
        title, description, avatar, views, followers = await TwitchHandler.fetchStreamInfo(stream.url, Key().twitchApiKey())
        
        emb = Embed()
        emb.title = title
        emb.type = 'rich'
        emb.description=description
        emb.url = stream.url
        emb.colour = Colour.purple()
        emb.set_footer(text='Created by PriestBot', icon_url=p.h2pIcon())
        emb.set_thumbnail(url=avatar)
        emb.set_author(name=member.name,icon_url=member.avatar_url)
        emb.add_field(name='Views', value=views)
        emb.add_field(name='Followers', value=followers)
                
        if currentlyStreaming not in member.roles:
            await member.add_roles(currentlyStreaming, reason='User started streaming')            
            await channel.send('{0.mention} is now Live on Twitch!'.format(member),embed=emb)
            
        else:
            # This could be slow, but shouldn't, assuming there should be few messages in the channel
            messages = await channel.history(limit=None).flatten()
        
            for message in messages:
                if member in message.mentions:
                    await message.edit(embed=emb)
        
        