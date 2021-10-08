'''Some stuff used for parsing text'''

def remove_strings(text): #wow i actually commented this very cool
    #get the start and end of every string
    quotepos = [] #here we'll store the index of every quote that's not been escaped
    for quote in ("'", "\""):
        allpos = [i for i in range(len(text)) if text.startswith(quote, i)] #gets all instances of each type of quotes
        for index in allpos:
            if text[index-1] != "\\":
                quotepos.append(index) #only pass to quotepos the strings that weren't escaped
    opened_quote = ""
    quotes = []
    for index in sorted(quotepos):
        if opened_quote == "": #no open quotes
            opened_quote = text[index]
            quotes.append(index)
        elif opened_quote == text[index]:       #current quote is the same as the open quote -> it closes, and
            quotes[-1] = (quotes[-1], index)    #otherwise it just gets ignored and treated as any other character
            opened_quote = ""
    if opened_quote != "":
        return None, None
    #now, replace them with things that won't be screwed up by the rest of input_format
    quotes.reverse() #this way the index numbers don't get fucked up
    c = 1
    quotetext = []
    for quote in quotes:
        quotetext = [text[quote[0]+1:quote[1]]] + quotetext
        text = text[:quote[0]] + f'"{len(quotes)-c}"' + text[quote[1]+1:] #"0", "1", etc.
        c += 1
    outquotes = [i.replace("\\'", "'").replace('\\"', '"') for i in quotetext] #gets all instances of each type of quotes
    return text, outquotes