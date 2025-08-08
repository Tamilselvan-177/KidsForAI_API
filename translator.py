import asyncio
from googletrans import Translator

async def Kids_translator():
    translator = Translator()
    result = await translator.translate("Hello, how are you?", src="en", dest="ta")
    print(result.text)  # Output will be in Tamil

asyncio.run(main())
