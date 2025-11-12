# Makefile per jack-ring-socket-server

# Nome dell'eseguibile
TARGET = jack-ring-socket-server

# File sorgente
SRCS = main.c argparser.c jackclient.c ringbuffer.c socketserver.c

# File header (opzionale, per dipendenze automatiche)
HEADERS = argparser.h ringbuffer.h jack-ring-socket-server.h jackclient.h socketserver.h

# Compilatore e flag
CC = gcc
CFLAGS = -Wall -Wextra -O2
LDFLAGS = -ljack -lpthread

# Regola di default
all: $(TARGET)

# Regola per compilare l'eseguibile
$(TARGET): $(SRCS) $(HEADERS)
	$(CC) $(CFLAGS) -o $(TARGET) $(SRCS) $(LDFLAGS)

# Regola per pulire i file compilati
clean:
	rm -f $(TARGET)

# Regola per eseguire
run: $(TARGET)
	./$(TARGET)

.PHONY: all clean run

