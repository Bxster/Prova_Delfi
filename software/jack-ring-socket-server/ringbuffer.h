/** @file ringbuffer.h
 * 
 */
 
#include <jack/jack.h> 
 
#ifndef RINGBUFFER
#define RINGBUFFER
 
 typedef struct ring_node_t {
    jack_default_audio_sample_t *data;
    struct ring_node_t *next;  
    unsigned short int populated; 
} ring_node, *p_ring_node;


typedef struct sample_ring_t{
    int len;
    unsigned short int populated;
    jack_nframes_t nframes;
    jack_nframes_t samplerate;
    int seconds;
    ring_node *last;  
} sample_ring;

int create_sample_ring(sample_ring *, int, jack_nframes_t, jack_nframes_t, int);
int ring_debug(sample_ring *);
int add_to_ring(sample_ring *, jack_default_audio_sample_t *);

#endif
