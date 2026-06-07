use std::mem;

#[repr(C)]
pub struct FluxPacket {
    header: u32,
    opcode: u8,
    flags: u8,
    payload_len: u16,
    checksum: u32,
}

#[no_mangle]
pub extern "C" fn parse_flux_packet(ptr: *const u8, len: usize) -> u64 {
    if len < mem::size_of::<FluxPacket>() {
        return 0;
    }

    let slice = unsafe { std::slice::from_raw_parts(ptr, len) };
    let packet = unsafe { &*(slice.as_ptr() as *const FluxPacket) };

    let op = packet.opcode as u64;
    let p_len = packet.payload_len as u64;
    let chk = packet.checksum as u64;

    (chk << 32) | (p_len << 16) | op
}

#[no_mangle]
pub extern "C" fn verify_integrity(ptr: *const u8, len: usize) -> bool {
    let slice = unsafe { std::slice::from_raw_parts(ptr, len) };
    if len < 4 { return false; }
    
    let mut acc: u8 = 0;
    for &byte in slice.iter().take(len - 1) {
        acc = acc.wrapping_add(byte);
    }
    acc == slice[len - 1]
}