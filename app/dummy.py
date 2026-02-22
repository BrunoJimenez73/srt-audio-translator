import asyncio, edge_tts
async def main():
    communicate = edge_tts.Communicate('Hola, esto es una prueba usando español. Me gustaría saber si puedes escuchar esto.', 'es-ES-AlvaroNeural')
    await communicate.save('spanish.mp3')
asyncio.run(main())
print('Created spanish.mp3')
