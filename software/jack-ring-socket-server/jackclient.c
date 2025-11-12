/** @file jackclient.c
 *  
 * Simple jack client that manage a single audio input port and populate the ringbuffer 
 *  
 */
 
 
#include "ringbuffer.h"
#include "jack-ring-socket-server.h"
#include "jackclient.h"
 
/** function process
 * This is a JACK callback function called every time there is a new audio block available.
 */
int process (jack_nframes_t nframes, void *arg)
{
    // Ottieni i buffer per i canali sinistro e destro
    jack_default_audio_sample_t *in_left;
    jack_default_audio_sample_t *in_right;

    in_left = jack_port_get_buffer(input_port_left, nframes);
    in_right = jack_port_get_buffer(input_port_right, nframes);

    // Combina i due canali in un array interlacciato (stereo)
    jack_default_audio_sample_t *stereo_data = malloc(sizeof(jack_default_audio_sample_t) * nframes * 2);
    if (stereo_data == NULL) {
        fprintf(stderr, "Memory allocation failed for stereo data\n");
        return 1; // Restituisci un errore
    }

    for (jack_nframes_t i = 0; i < nframes; i++) {
        stereo_data[i * 2] = in_left[i];   // Canale sinistro
        stereo_data[i * 2 + 1] = in_right[i]; // Canale destro
    }

    // Aggiungi i dati interlacciati al ring buffer
    add_to_ring(&MyRing, stereo_data);

    // Libera la memoria allocata per i dati stereo
    free(stereo_data);

    return 0;      
}


/**
 * JACK calls this shutdown_callback if the server ever shuts down or
 * decides to disconnect the client.
 */
void jack_shutdown (void *arg) {
	exit (1);
}
