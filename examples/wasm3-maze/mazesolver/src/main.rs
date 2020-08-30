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


// min-heap of unvisited cells with weights in static memory
static mut UNVISITED: [(u16, u16, i32); 0x1000] = [(0, 0, 0); 0x1000];
static mut UNVISITED_SIZE: usize = 0;

fn unvisited_push(x: usize, y: usize, h: i32) -> Result<()> {
    // best effort with small space
    let x = u16::try_from(x).map_err(|_| Error::TooBig)?;
    let y = u16::try_from(y).map_err(|_| Error::TooBig)?;

    let unvisited = unsafe { &mut UNVISITED };
    let unvisited_size = unsafe { &mut UNVISITED_SIZE };
    if *unvisited_size == unvisited.len() {
        Err(Error::NoMem)?;
    }

    // insert at end
    unvisited[*unvisited_size] = (x, y, h);
    *unvisited_size += 1;

    // maintain heap invariant
    let mut i = *unvisited_size-1;
    while i > 0 {
        let p = (i-1) / 2;
        if unvisited[p].2 <= unvisited[i].2 {
            break
        };

        unvisited.swap(p, i);
        i = p;
    }

    Ok(())
}
fn unvisited_pop() -> Result<(usize, usize, i32)> {
    let unvisited = unsafe { &mut UNVISITED };
    let unvisited_size = unsafe { &mut UNVISITED_SIZE };
    if *unvisited_size == 0 {
        Err(Error::Dom)?;
    }

    // heap invariant means first cell is best cell
    let (x, y, h) = unvisited[0];
    unvisited[0] = unvisited[*unvisited_size-1];
    *unvisited_size -= 1;

    // maintain heap invariant
    let mut i = 0;
    while i < *unvisited_size {
        let l = 2*i + 1;
        let r = 2*i + 2;
        if l < *unvisited_size
                && unvisited[l].2 < unvisited[i].2
                && unvisited[l].2 < unvisited[r].2 {
            unvisited.swap(l, i);
            i = l;
        } else if r < *unvisited_size
                && unvisited[r].2 < unvisited[i].2 {
            unvisited.swap(r, i);
            i = r;
        } else {
            break;
        }
    }

    Ok((usize::from(x), usize::from(y), h))
}


// solver using A*
#[export(export::maze_solve)]
pub fn maze_solve(
    startx: usize, starty: usize,
    endx: usize, endy: usize
) -> Result<u32> {
    let (maze, width, height) = getmaze()?;
    let inbounds = |x, y| x < width && y < height;

    // distance based heuristic
    let heuristic = |x, y| {
        let diffx = (endx as i32)-(x as i32);
        let diffy = (endy as i32)-(y as i32);
        diffx*diffx + diffy*diffy
    };

    let (mut x, mut y) = (startx, starty);
    while x != endx || y != endy {
        let mut visit = |x, y, v| {
            if inbounds(x, y) && maze[x + y*width] == 0 {
                unvisited_push(x, y, heuristic(x, y))?;
                maze[x + y*width] = v;
            }
            Ok(())
        };

        // add neighbors to search list and add references to search path
        visit(x,                      y+1,                    0x10)?;
        visit(x+1,                    y+1,                    0x20)?;
        visit(x+1,                    y,                      0x30)?;
        visit(x+1,                    y.overflowing_sub(1).0, 0x40)?;
        visit(x,                      y.overflowing_sub(1).0, 0x50)?;
        visit(x.overflowing_sub(1).0, y.overflowing_sub(1).0, 0x60)?;
        visit(x.overflowing_sub(1).0, y,                      0x70)?;
        visit(x.overflowing_sub(1).0, y+1,                    0x80)?;

        // find next best
        let (nx, ny) = match unvisited_pop() {
            Ok((x, y, _))               => (x, y),
            Err(x) if x == Error::Dom   => break,
            Err(x)                      => Err(x)?,
        };

        x = nx;
        y = ny;
    }

    // ok! build up path
    let (mut x, mut y) = (endx, endy);
    loop {
        // keep track of this temporarily
        let p = maze[x + y*width];

        // mark path!
        maze[x + y*width] = 2;

        // find next path coord?
        match p {
            0x10 => { x = x;   y = y-1; },
            0x20 => { x = x-1; y = y-1; },
            0x30 => { x = x-1; y = y;   },
            0x40 => { x = x-1; y = y+1; },
            0x50 => { x = x;   y = y+1; },
            0x60 => { x = x+1; y = y+1; },
            0x70 => { x = x+1; y = y;   },
            0x80 => { x = x+1; y = y-1; },
            _    => break,
        }
    }

    // throw away everthing else
    for y in 0..height {
        for x in 0..width {
            maze[x + y*width] &= 0x0f;
        }
    }

    setmaze(maze)?;
    Ok(0)
}

