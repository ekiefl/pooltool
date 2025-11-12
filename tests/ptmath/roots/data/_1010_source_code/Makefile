.PHONY: all clean benchmark

all: libquartic.so

libquartic.so: quartic_solver.c
	$(CC) -shared -fPIC -O3 -o libquartic.so quartic_solver.c -lm

benchmark: benchmark.c quartic_solver.c
	$(CC) -O3 -o benchmark benchmark.c quartic_solver.c -lm

sources: quartic_solver_cmplx.o quartic_solver.o

quartic_solver_cmplx.o: quartic_solver_cmplx.c
	$(CC) $(OF) $(CFLAGS) -c quartic_solver_cmplx.c

quartic_solver.o: quartic_solver.c
	$(CC) $(OF) $(CFLAGS) -c quartic_solver.c

clean:
	rm -f *.o libquartic.so benchmark 
