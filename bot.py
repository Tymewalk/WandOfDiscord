# WandOfDiscord
# Created by Tymewalk
# https://github.com/Tymewalk
import pexpect, inspect, traceback, discord, asyncio, subprocess, vscreen, os, json, re

client = discord.Client()

# Load the settings - we need this for the token and player name
f = open("{}/{}".format(os.path.dirname(os.path.realpath(__file__)), "settings.json"))
settings = json.load(f)
f.close()

playername = settings["playername"]

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    await client.change_presence(game=discord.Game(name="Use n!help"))

print("Setting up VScreen... ")
nethack_screen = vscreen.VScreen(80, 24)
pointer_x = 0
pointer_y = 0
print("VScreen set up successfully.")

print("Spawning NetHack... ")
nh = pexpect.spawn("nethack", ["-u", playername])
print("Spawned.")

print("Reading screen... ", end='')
line = nh.read_nonblocking(size=999999999).decode()

async def parse_nethack_output(output, message=False):
    global pointer_x, pointer_y, nethack_screen
    # Strip the garbage.
    # [Xm and [XXm are ANSI formatting, we don't print those since Discord code tags don't support them.
    # [?1049h enables the alternate screen buffer. We don't care about that at all because Discord's surely not gonna use it.
    # Newlines are handled via \r.
    stripped = str(re.sub("(\[[0-9](|[0-9])m|\[\?1049h|\n)", "", output))
    counter = 0
    # skip_to allows us to skip instructions we've already processed.
    skip_to = 0
    for i in stripped:
        # Check - if counter >= skip_to, we've skipped the instructions
        # we've already processed and are ready to start reading new
        # instructions
        if counter >= skip_to:
            # These instructions are all ANSI escape codes
            # https://en.wikipedia.org/wiki/ANSI_escape_code#Escape_sequences
            try:
                # Normally I would strip the \x1b here, but unfortunately for us, Nethack uses [ as armor.
                # So to avoid having any conflict, we check for it.
                if i == "" and stripped[counter + 1] == "[":
                    if stripped[counter + 2] == "H":
                        # [H alone means go to 0,0
                        # You'll notice it being printed when we use the status bar
                        pointer_x = 0
                        pointer_y = 0
                        skip_to = counter + 3
                    elif stripped[counter + 2] == "C":
                        # Move right
                        pointer_x += 1
                        skip_to = counter + 3
                    elif stripped[counter + 2] == "D":
                        # Move left
                        pointer_x += -1
                        skip_to = counter + 3
                    elif stripped[counter + 2] == "A":
                        # Move up
                        pointer_y += -1
                        skip_to = counter + 3
                    elif stripped[counter + 2] == "B":
                        # Move down
                        pointer_y += 1
                        skip_to = counter + 3
                    elif stripped[counter + 2] == "K":
                        # [K means clear the rest of this line
                        # It's used in the upper status bar
                        nethack_screen.blit(" "*(80 - pointer_x), pointer_x, pointer_y)
                        skip_to = counter + 3
                    elif stripped[counter + 3] == "K":
                        # However, other [nK for values of n can change what is cleared
                        if stripped[counter + 2] == "1":
                            # [1K means clear the beginning of this line
                            nethack_screen.blit(" "*pointer_x, pointer_x, pointer_y)
                            skip_to = counter + 4
                        elif stripped[counter + 2] == "2":
                            # [2K means clear all of this line.
                            nethack_screen.blit(" "*80, pointer_y)
                            skip_to = counter + 4
                    elif stripped[counter + 3] == ";":
                        # [XX;YYH tells the pointer to go to XX, YY.
                        # The different checks just figure how long those numbers are.
                        if not counter + 6 > len(stripped) - 1:
                            if stripped[counter + 6] == "H":
                                pointer_y = int(str(stripped[counter + 2])) - 1
                                pointer_x = int(str(stripped[counter + 4]) + str(stripped[counter + 5])) - 1
                                skip_to = counter + 7

                        if not counter + 5 > len(stripped) - 1:
                            if stripped[counter + 5] == "H":
                                pointer_y = int(str(stripped[counter + 2])) - 1
                                pointer_x = int(str(stripped[counter + 4])) - 1
                                skip_to = counter + 6
                    elif stripped[counter + 4] == ";":
                        # We have to check if we're not going past the end of the string. Otherwise, it's gonna skip the
                        # instruction and blit it to the screen instead.
                        if not counter + 7 > len(stripped) - 1:
                            if stripped[counter + 7] == "H":
                                pointer_y = int(str(stripped[counter + 2]) + str(stripped[counter + 3])) - 1
                                pointer_x = int(str(stripped[counter + 5]) + str(stripped[counter + 6])) - 1
                                skip_to = counter + 8
                        if not counter + 6 > len(stripped) - 1:
                            if stripped[counter + 6] == "H":
                                pointer_y = int(str(stripped[counter + 2]) + str(stripped[counter + 3])) - 1
                                pointer_x = int(str(stripped[counter + 5])) - 1
                                skip_to = counter + 7
                    elif stripped[counter + 3] == "J":
                        # [nJ clears part of the screen. n changes how it works.
                        if stripped[counter + 2] == "2":
                            # [2J clears the whole screen.
                            # This is the only one I've seen NetHack use
                            nethack_screen.clear()
                        skip_to = counter + 4
                    else:
                        # If none of these worked, we do nothing. This way we don't have any wrong usage.
                        #nethack_screen.blit(i, pointer_x, pointer_y)
                        #pointer_x = pointer_x + 1
                        pass
                elif i == chr(13):
                    # 0x0d, or \r, is a carriage return
                    pointer_y = pointer_y + 1
                elif i == "":
                    # 0x08, or \b, is a backspace
                    pointer_x = pointer_x - 1
                else:
                    nethack_screen.blit(i, pointer_x, pointer_y)
                    pointer_x = pointer_x + 1
            except IndexError:
                print("Hit end of line unexpectedly - ignoring commands")
            finally:
                pass
        counter += 1

#await parse_nethack_output(line)

async def show_current_board(message):
    global nh, line, client, nethack_screen

    line = nh.read_nonblocking(size=9999).decode()
    await parse_nethack_output(line)
    await client.send_message(message.channel, "{} ```{}```".format(message.author.mention, nethack_screen.get_screen()))

@client.event
async def on_message(message):
    global nh, line, nethack_screen, pointer_x, pointer_y
    if message.author.id == client.user.id:
        pass

    if re.search("^n!help", message.content):
        await client.send_message(message.channel, "{} Commands: n!board, n!help, n!up, n!down, n!left, n!right, n!n, n!key <letter to send>, n!control <control key to send>".format(message.author.mention))
    elif re.search("^n!board", message.content):
        await show_current_board(message)
    elif re.search("^n!up", message.content):
        if len(message.content) > 4:
            try:
                # Try getting the number of steps by stripping whitespace
                steps = int(message.content[4:].rstrip().lstrip())
            except:
                # Clearly it didn't work
                await client.send_message(message.channel, "{} You need to provide an integer as the number of times!".format(message.author.mention))
                steps = 1
            finally:
                for i in range(steps):
                    nh.send("k")
        # Send out the game board
        await show_current_board(message)
    elif re.search("^n!down", message.content):
        if len(message.content) > 6:
            try:
                # Try getting the number of steps by stripping whitespace
                steps = int(message.content[6:].rstrip().lstrip())
            except:
                # Clearly it didn't work
                await client.send_message(message.channel, "{} You need to provide an integer as the number of times!".format(message.author.mention))
                steps = 1
            finally:
                for i in range(steps):
                    nh.send("j")
        # Send out the game board
        await show_current_board(message)
    elif re.search("^n!left", message.content):
        if len(message.content) > 6:
            try:
                # Try getting the number of steps by stripping whitespace
                steps = int(message.content[6:].rstrip().lstrip())
            except:
                # Clearly it didn't work
                await client.send_message(message.channel, "{} You need to provide an integer as the number of times!".format(message.author.mention))
                steps = 1
            finally:
                for i in range(steps):
                    nh.send("h")
        # Send out the game board
        await show_current_board(message)
    elif re.search("^n!right", message.content):
        if len(message.content) > 7:
            try:
                # Try getting the number of steps by stripping whitespace
                steps = int(message.content[7:].rstrip().lstrip())
            except:
                # Clearly it didn't work
                await client.send_message(message.channel, "{} You need to provide an integer as the number of times!".format(message.author.mention))
                steps = 1
            finally:
                for i in range(steps):
                    nh.send("l")
        # Send out the game board
        await show_current_board(message)
    elif re.search("^n!yes", message.content):
        nh.send("y")
        # Send out the game board
        await show_current_board(message)
    elif re.search("^n!no", message.content):
        nh.send("n")
        await show_current_board(message)
    elif re.search("^n!space", message.content):
        nh.send(" ")
        await show_current_board(message)
    elif re.search("^n!return", message.content):
        nh.send("\r")
        await show_current_board(message)
    elif re.search("^n!y", message.content):
        nh.send("y")
        await show_current_board(message)
    elif re.search("^n!n", message.content):
        nh.send("n")
        await show_current_board(message)
    elif re.search("^n!save", message.content):
        nh.send("S")
        await show_current_board(message)
    elif re.search("^n!key ", message.content):
        # Send arbitrary keys. Useful for many things
        for k in message.content[6:]:
            nh.send(k)
        await show_current_board(message)
    elif re.search("^n!control ", message.content):
        # Send a control key
        nh.sendcontrol(message.content[10])
        await show_current_board(message)
    elif re.search("^n!debug", message.content):
        print("Caught a debug command!")
        try:
            result = eval(message.content[8:])
            if inspect.isawaitable(result):
                result = await result
        except Exception as e:
            result = repr(e)
        if len(str(result)) < 1998:
            await client.send_message(message.author, "`{}`".format(result))
        else:
            await client.send_message(message.author, "`{}`".format(result)[0:1999])


try:
    client.run(settings["token"])
except KeyboardInterrupt:
    client.logout()
finally:
    print("Done running.")
