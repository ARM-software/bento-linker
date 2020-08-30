#![no_std]
use bb::*;
use core::convert::TryFrom;


// maze access things
// the static array provides an alternative to
// heap allocation
static mut MAZE: [u8; 0x6400] = [0; 0x6400];

fn getmaze() -> Result<(&'static mut [u8], usize, usize)> {
    // get width and height from system
    let width = import::maze_getwidth();
    let height = import::maze_getwidth();

    // we're not multithreaded so this is fine
    let maze = &mut unsafe { &mut MAZE }[..width*height];
    // get maze from system
    import::maze_getall(maze)?;

    Ok((maze, width, height))
}

fn setmaze(maze: &mut [u8]) -> Result<()> {
    import::maze_setall(maze)
}


// statically allocated array of unvisited cells
// for Prim's algorithm
static mut UNVISITED: [(u16, u16); 0x1900] = [(0, 0); 0x1900];
static mut UNVISITED_SIZE: usize = 0;

fn unvisited_push(x: usize, y: usize) -> Result<()> {
    // best effort with small space
    let x = u16::try_from(x).map_err(|_| Error::TooBig)?;
    let y = u16::try_from(y).map_err(|_| Error::TooBig)?;

    let unvisited = unsafe { &mut UNVISITED };
    let unvisited_size = unsafe { &mut UNVISITED_SIZE };
    if *unvisited_size == unvisited.len() {
        Err(Error::NoMem)?;
    }

    unvisited[*unvisited_size] = (x, y);
    *unvisited_size += 1;

    Ok(())
}

fn unvisited_pop(i: usize) -> Result<(usize, usize)> {
    let unvisited = unsafe { &mut UNVISITED };
    let unvisited_size = unsafe { &mut UNVISITED_SIZE };
    if i >= *unvisited_size {
        Err(Error::Dom)?;
    }

    let (x, y) = unvisited[i];
    unvisited[i] = unvisited[*unvisited_size-1];
    *unvisited_size -= 1;

    Ok((usize::from(x), usize::from(y)))
}

fn unvisited_pop_random() -> Result<(usize, usize)> {
    let x: u32 = import::random_get();
    let x = usize::try_from(x).map_err(|_| Error::TooBig)?;
    let unvisited_size = unsafe { UNVISITED_SIZE };
    if unvisited_size == 0 {
        Err(Error::Dom)?;
    }

    unvisited_pop(x % unvisited_size)
}

fn unvisited_contains(x: usize, y: usize) -> bool {
    // best effort with small space
    let x = match u16::try_from(x) {
        Ok(x) => x,
        _ => return false,
    };
    let y = match u16::try_from(y) {
        Ok(y) => y,
        _ => return false,
    };

    let unvisited = unsafe { &UNVISITED };
    let unvisited_size = unsafe { UNVISITED_SIZE };
    for i in 0..unvisited_size {
        if unvisited[i] == (x, y) {
            return true;
        }
    }

    false
}


// maze building algorithm
// https://kairumagames.com/blog/cavetutorial

// maze generation with Prim's algorithm
#[export(export::maze_generate_prim)]
pub fn maze_generate_prim(startx: usize, starty: usize) -> Result<()> {
    let (maze, width, height) = getmaze()?;
    let inbounds = |x, y| x < width-1 && y < height-1;

    let (mut x, mut y) = (startx, starty);
    loop {
        // clear cell
        maze[x + y*width] = 0;

        // add unvisited neighbors
        let visit = |x, y| {
            if inbounds(x, y) && maze[x+y*width] == 1
                    && !unvisited_contains(x, y) {
                unvisited_push(x, y)?;
            }
            Ok(())
        };

        visit(x, y+2)?;
        visit(x+2, y)?;
        visit(x, y.overflowing_sub(2).0)?;
        visit(x.overflowing_sub(2).0, y)?;

        // choose random new cell
        let (nx, ny) = match unvisited_pop_random() {
            Ok((x, y))                => (x, y),
            Err(x) if x == Error::Dom => break,
            Err(x)                    => Err(x)?,
        };

        x = nx;
        y = ny;

        // choose one wall randomly
        let (wx, wy) = loop {
            let choose = |x, y| {
                inbounds(x, y) && maze[x + y*width] == 0 &&
                    import::random_get() & 1 == 1
            };

            if choose(x, y+2)                    { break (x, y+1); }
            if choose(x+2, y)                    { break (x+1, y); }
            if choose(x, y.overflowing_sub(2).0) { break (x, y-1); }
            if choose(x.overflowing_sub(2).0, y) { break (x-1, y); }
        };

        maze[wx + wy*width] = 0;
    }

    setmaze(maze)
}

// remove dead ends, again from this blog post which contains
// several neat ideas!
// https://kairumagames.com/blog/cavetutorial
#[export(export::maze_reduce)]
pub fn maze_reduce(iterations: u32) -> Result<()> {
    let (maze, width, height) = getmaze()?;
    let inbounds = |x, y| x < width && y < height;

    for _ in 0..iterations {
        for y in 1..height-1 {
            for x in 1..width-1 {
                if maze[x + y*width] == 0 {
                    let mut neighbors = 0;
                    let mut visit = |x, y| {
                        if inbounds(x, y) && maze[x + y*width] & 1 == 0 {
                            neighbors += 1;
                        }
                    };

                    visit(x, y+1);
                    visit(x+1, y);
                    visit(x, y.overflowing_sub(1).0);
                    visit(x.overflowing_sub(1).0, y);

                    if neighbors <= 1 {
                        maze[x + y*width] = 2;
                    }
                }
            }
        }

        // two passes to avoid sweeping out whole rows
        for y in 0..height {
            for x in 0..width {
                if maze[x + y*width] == 2 {
                    maze[x + y*width] = 1;
                }
            }
        }
    }

    setmaze(maze)
}


// cellular automata to grow caves, again from
// https://kairumagames.com/blog/cavetutorial
#[export(export::maze_erode)]
pub fn maze_erode(iterations: u32) -> Result<()> {
    let (maze, width, height) = getmaze()?;
    let inbounds = |x, y| x < width && y < height;

    for _ in 0..iterations {
        for y in 1..height-1 {
            for x in 1..width-1 {
                if maze[x + y*width] == 1 {
                    let mut neighbors = 0;
                    for x2 in 0..3 {
                        for y2 in 0..3 {
                            if inbounds(x+x2-1, y+y2-1)
                                    && maze[(x+x2-1) + (y+y2-1)*width] == 0 {
                                neighbors += 1;
                            }
                        }
                    }

                    if neighbors >= 4 {
                        maze[x + y*width] = 3;
                    }
                }
            }
        }

        // two passes to avoid sweeping out whole rows
        for y in 0..height {
            for x in 0..width {
                if maze[x + y*width] == 3 {
                    maze[x + y*width] = 0;
                }
            }
        }
    }

    setmaze(maze)
}

// find best start/stop, this is a bit naive at the moment
#[export(export::maze_findstart)]
pub fn maze_findstart(sx: &mut usize, sy: &mut usize) -> Result<()> {
    let (maze, width, height) = getmaze()?;

    let heuristic = |x, y| {
        let diffx = (x as i32)-0;
        let diffy = (y as i32)-0;
        diffx*diffx + diffy*diffy
    };

    let (mut bestx, mut besty, mut besth) = (2, 2, i32::MAX);
    for y in 2..height {
        for x in 2..width {
            if maze[x + y*width] == 0 {
                let h = heuristic(x, y);
                if h <= besth {
                    bestx = x;
                    besty = y;
                    besth = h;
                }
            }
        }
    }

    *sx = bestx;
    *sy = besty;
    Ok(())
}

#[export(export::maze_findend)]
pub fn maze_findend(ex: &mut usize, ey: &mut usize) -> Result<()> {
    let (maze, width, height) = getmaze()?;

    let heuristic = |x, y| {
        let diffx = (x as i32)-(width as i32-1);
        let diffy = (y as i32)-(height as i32-1);
        diffx*diffx + diffy*diffy
    };

    let (mut bestx, mut besty, mut besth) = (2, 2, i32::MAX);
    for y in (0..height-2).rev() {
        for x in (0..width-2).rev() {
            if maze[x + y*width] == 0 {
                let h = heuristic(x, y);
                if h <= besth {
                    bestx = x;
                    besty = y;
                    besth = h;
                }
            }
        }
    }

    *ex = bestx;
    *ey = besty;
    Ok(())
}
