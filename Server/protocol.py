DELIMITER = "|"

def create_message(command, *args):
    return DELIMITER.join([command] + list(args))

def parse_message(message):
    parts = message.split(DELIMITER)
    command = parts[0]
    args = parts[1:]
    return command, args