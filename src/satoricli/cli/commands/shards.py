import time
import os
from argparse import ArgumentParser
from pathlib import Path
import struct
import socket
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
import hashlib
from netaddr import IPNetwork
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from satoricli.cli.commands.base import BaseCommand
from satoricli.cli.utils import console, error_console


class ShardsCommand(BaseCommand):
    name = "shards"

    def register_args(self, parser: ArgumentParser):
        parser.add_argument("--shard", required=True, help="Current shard and total (X/Y format)")
        parser.add_argument("--seed", type=int, default=1, help="Seed for pseudorandom permutation (default: 1)")
        parser.add_argument("--input", dest="input_file", required=True, help="Input file with addresses OR direct IP/CIDR (e.g., 192.168.1.0/24, 10.0.0.1-10.0.0.255)")
        parser.add_argument("--exclude", dest="exclude_file", help="File with addresses to exclude OR direct IP/CIDR to exclude (e.g., 192.168.1.0/24)")
        parser.add_argument("--results", dest="results_file", help="Save results to text file (must have .txt extension or no extension; default is .txt)")

    def is_direct_input(self, input_str: str) -> bool:
        """Check if input is a direct IP/CIDR/range instead of a file path"""
        if '/' in input_str and self.is_valid_cidr(input_str):
            return True
        if '-' in input_str and self.is_valid_ip_range(input_str):
            return True
        if self.is_ip_address(input_str):
            return True
        if not os.path.exists(input_str) and ('.' in input_str or ':' in input_str):
            return True
        return False
    
    def is_valid_cidr(self, cidr_str: str) -> bool:
        """Check if string is a valid CIDR notation"""
        try:
            IPNetwork(cidr_str)
            return True
        except:
            return False
    
    def is_valid_ip_range(self, range_str: str) -> bool:
        """Check if string is a valid IP range (e.g., 192.168.1.1-192.168.1.255)"""
        if '-' not in range_str:
            return False
        try:
            start_ip, end_ip = range_str.split('-', 1)
            return self.is_ip_address(start_ip.strip()) and self.is_ip_address(end_ip.strip())
        except:
            return False

    def ip_to_int(self, ip_str: str) -> int:
        """Convert IP string to integer using fast socket.inet_aton"""
        try:
            return struct.unpack("!I", socket.inet_aton(ip_str))[0]
        except socket.error:
            return None

    def is_ip_address(self, value: str) -> bool:
        """Check if string is an IP address"""
        try:
            socket.inet_aton(value)
            return True
        except socket.error:
            return False
    
    def hash_string(self, text: str, seed: int) -> int:
        """Hash any string (domain/URL) for shard selection"""
        hash_input = f"{text}:{seed}".encode('utf-8')
        hash_bytes = hashlib.sha256(hash_input).digest()
        return struct.unpack("!I", hash_bytes[:4])[0] & 0x7fffffff

    def extract_domain_from_entry(self, entry: str) -> str:
        """Extract domain/URL from entry, removing common prefixes and ports"""
        for prefix in ['http://', 'https://', 'ftp://', '//']:
            if entry.startswith(prefix):
                entry = entry[len(prefix):]
                break
        
        if ':' in entry and self.is_ip_address(entry.split(':')[0]):
            return entry.split(':')[0]
        
        return entry

    def build_blacklist_ranges(self, file_path: str) -> list:
        """Build sorted list of (start, end) integer ranges for faster lookup"""
        ranges = []
        
        if self.is_direct_input(file_path):
            entry = file_path.strip()
            try:
                if ':' in entry and '/' not in entry and '-' not in entry:
                    parts = entry.split(':')
                    if self.is_ip_address(parts[0]):
                        entry = parts[0]
                
                if '/' in entry and (self.is_ip_address(entry.split('/')[0]) or '.' in entry.split('/')[0]):
                    network = IPNetwork(entry)
                    ranges.append((int(network.first), int(network.last)))
                elif '-' in entry:
                    start_ip, end_ip = entry.split('-')
                    start_int = self.ip_to_int(start_ip.strip())
                    end_int = self.ip_to_int(end_ip.strip())
                    if start_int and end_int:
                        ranges.append((start_int, end_int))
                elif self.is_ip_address(entry):
                    ip_int = self.ip_to_int(entry)
                    if ip_int:
                        ranges.append((ip_int, ip_int))
            except Exception:
                pass
        else:
            with open(file_path, 'r') as f:
                for line in f:
                    entry = line.strip()
                    if not entry or entry.startswith("#"):
                        continue
                    try:
                        if ':' in entry and '/' not in entry and '-' not in entry:
                            parts = entry.split(':')
                            if self.is_ip_address(parts[0]):
                                entry = parts[0]
                        
                        if '/' in entry and (self.is_ip_address(entry.split('/')[0]) or '.' in entry.split('/')[0]):
                            network = IPNetwork(entry)
                            ranges.append((int(network.first), int(network.last)))
                        elif '-' in entry:
                            start_ip, end_ip = entry.split('-')
                            start_int = self.ip_to_int(start_ip.strip())
                            end_int = self.ip_to_int(end_ip.strip())
                            if start_int and end_int:
                                ranges.append((start_int, end_int))
                        elif self.is_ip_address(entry):
                            ip_int = self.ip_to_int(entry)
                            if ip_int:
                                ranges.append((ip_int, ip_int))
                    except Exception:
                        continue
        
        ranges.sort()
        
        merged = []
        for start, end in ranges:
            if merged and start <= merged[-1][1] + 1:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        
        return merged

    def is_range_completely_blacklisted(self, range_start: int, range_end: int, blacklist_ranges: list) -> bool:
        """Check if entire range is covered by exclude list - ULTRA FAST SKIP"""
        if not blacklist_ranges:
            return False
            
        left, right = 0, len(blacklist_ranges) - 1
        
        while left <= right:
            mid = (left + right) >> 1
            bl_start, bl_end = blacklist_ranges[mid]
            
            if bl_start <= range_start and bl_end >= range_end:
                return True
                
            if bl_end < range_start:
                left = mid + 1
            elif bl_start > range_end:
                right = mid - 1
            else:
                return False
        
        return False

    def is_ip_in_ranges_vectorized(self, ip_array: np.ndarray, ranges: list) -> np.ndarray:
        """Vectorized exclude list check using numpy for massive speedup"""
        if not ranges or len(ip_array) == 0:
            return np.zeros(len(ip_array), dtype=bool)
            
        starts = np.array([r[0] for r in ranges])
        ends = np.array([r[1] for r in ranges])
        
        ip_expanded = ip_array[:, np.newaxis] 
        starts_expanded = starts[np.newaxis, :] 
        ends_expanded = ends[np.newaxis, :]    
        
        in_range = (ip_expanded >= starts_expanded) & (ip_expanded <= ends_expanded)
        return np.any(in_range, axis=1)

    def is_ip_in_ranges(self, ip_int: int, ranges: list) -> bool:
        """Optimized binary search with early termination - fallback for single IPs"""
        if not ranges:
            return False
            
        if ip_int < ranges[0][0] or ip_int > ranges[-1][1]:
            return False
            
        left, right = 0, len(ranges) - 1
        
        while left <= right:
            mid = (left + right) >> 1
            start, end = ranges[mid]
            
            if ip_int < start:
                right = mid - 1
            elif ip_int > end:
                left = mid + 1
            else:
                return True
        
        return False

    def hash_ip_int_vectorized(self, ip_array: np.ndarray, seed: int) -> np.ndarray:
        """Vectorized hash computation using numpy - MASSIVE speedup"""

        hash_vals = np.full(ip_array.shape, 2166136261, dtype=np.uint64)  
        for shift in [0, 8, 16, 24]:
            byte_vals = (ip_array >> shift) & 0xff
            hash_vals ^= byte_vals
            hash_vals *= 16777619
            hash_vals = hash_vals.astype(np.uint64)
        
        hash_vals ^= seed
        hash_vals *= 16777619
        
        return (hash_vals & 0x7fffffff).astype(np.uint32)

    def hash_ip_int(self, ip_int: int, seed: int) -> int:
        """Fast hash using integer directly - fallback for single IPs"""
        hash_val = 2166136261  
        hash_val ^= ip_int & 0xff
        hash_val *= 16777619
        hash_val ^= (ip_int >> 8) & 0xff
        hash_val *= 16777619
        hash_val ^= (ip_int >> 16) & 0xff
        hash_val *= 16777619
        hash_val ^= (ip_int >> 24) & 0xff
        hash_val *= 16777619
        hash_val ^= seed
        hash_val *= 16777619
        return hash_val & 0x7fffffff

    def int_to_ip_str(self, ip_int: int) -> str:
        """Convert integer to IP string"""
        return socket.inet_ntoa(struct.pack("!I", ip_int))

    def subtract_blacklist_from_range(self, range_start: int, range_end: int, blacklist_ranges: list) -> list:
        """HARDCORE: Pre-filter exclude list to get only valid IP segments - MASSIVE speedup"""
        if not blacklist_ranges:
            return [(range_start, range_end)]
        
        valid_segments = []
        current_start = range_start
        
        for bl_start, bl_end in blacklist_ranges:
            if bl_end < range_start or bl_start > range_end:
                continue

            if current_start < bl_start:
                valid_segments.append((current_start, min(bl_start - 1, range_end)))
            
            current_start = max(current_start, bl_end + 1)
            
            if current_start > range_end:
                break
        
        if current_start <= range_end:
            valid_segments.append((current_start, range_end))
        
        return valid_segments

    def process_ip_range_pre_filtered(self, range_start: int, range_end: int, blacklist_ranges: list, 
                                    shard_x: int, shard_y: int, seed: int) -> tuple:
        """ULTRA-FAST: Process only non-excluded segments - skip billions of excluded IPs"""
        
        valid_segments = self.subtract_blacklist_from_range(range_start, range_end, blacklist_ranges)
        
        if not valid_segments:
            total_processed = range_end - range_start + 1
            return total_processed, total_processed, []
        
        total_processed = range_end - range_start + 1
        total_excluded = total_processed - sum(seg_end - seg_start + 1 for seg_start, seg_end in valid_segments)
        selected_ips = []
        
        for seg_start, seg_end in valid_segments:
            seg_size = seg_end - seg_start + 1
            
            if seg_size > 100000:
                chunk_size = 1000000
                
                for chunk_start in range(seg_start, seg_end + 1, chunk_size):
                    chunk_end = min(chunk_start + chunk_size - 1, seg_end)
                    
                    ip_array = np.arange(chunk_start, chunk_end + 1, dtype=np.uint32)
                    
                    hash_values = self.hash_ip_int_vectorized(ip_array, seed)
                    
                    shard_mask = (hash_values % shard_y) == (shard_x - 1)
                    selected_ip_ints = ip_array[shard_mask]
                    
                    for ip_int in selected_ip_ints:
                        selected_ips.append(self.int_to_ip_str(int(ip_int)))
            else:
                for ip_int in range(seg_start, seg_end + 1):
                    hash_val = self.hash_ip_int(ip_int, seed)
                    if (hash_val % shard_y) == (shard_x - 1):
                        selected_ips.append(self.int_to_ip_str(ip_int))
        
        return total_processed, total_excluded, selected_ips

    def parse_direct_input(self, input_str: str) -> tuple:
        """Parse direct input and return (ip_ranges, non_ip_entries)"""
        ip_ranges = []
        non_ip_entries = []
        
        entry = input_str.strip()
        try:
            if ':' in entry and '/' not in entry and '-' not in entry:
                parts = entry.split(':')
                if self.is_ip_address(parts[0]):
                    entry = parts[0]
            
            if '/' in entry and (self.is_ip_address(entry.split('/')[0]) or 
                (entry.count('.') >= 3 and '-' not in entry)):
                network = IPNetwork(entry)
                ip_ranges.append((int(network.first), int(network.last)))
            elif '-' in entry and self.is_ip_address(entry.split('-')[0].strip()):
                start_ip, end_ip = entry.split('-')
                start_int = self.ip_to_int(start_ip.strip())
                end_int = self.ip_to_int(end_ip.strip())
                if start_int and end_int:
                    ip_ranges.append((start_int, end_int))
            elif self.is_ip_address(entry):
                ip_int = self.ip_to_int(entry)
                if ip_int:
                    ip_ranges.append((ip_int, ip_int))
            else:
                clean_entry = self.extract_domain_from_entry(entry)
                if clean_entry:
                    non_ip_entries.append(clean_entry)
        except Exception:
            clean_entry = self.extract_domain_from_entry(entry)
            if clean_entry:
                non_ip_entries.append(clean_entry)
        
        return ip_ranges, non_ip_entries

    def read_file_addresses_ultra_parallel(self, file_path: str, blacklist_ranges: list, shard_x: int, shard_y: int, seed: int, total_items: int) -> tuple:
        """Ultra parallel processing with dynamic work queue for perfect load balancing"""
        
        num_processes = mp.cpu_count()
        
        ip_ranges = []
        non_ip_entries = []
        
        if self.is_direct_input(file_path):
            ip_ranges, non_ip_entries = self.parse_direct_input(file_path)
        else:
            with open(file_path, 'r') as f:
                for line in f:
                    entry = line.strip()
                    if not entry or entry.startswith("#"):
                        continue
                    try:
                        if ':' in entry and '/' not in entry and '-' not in entry:
                            parts = entry.split(':')
                            if self.is_ip_address(parts[0]):
                                entry = parts[0]
                        
                        if '/' in entry and (self.is_ip_address(entry.split('/')[0]) or 
                            (entry.count('.') >= 3 and '-' not in entry)):
                            network = IPNetwork(entry)
                            ip_ranges.append((int(network.first), int(network.last)))
                        elif '-' in entry and self.is_ip_address(entry.split('-')[0].strip()):
                            start_ip, end_ip = entry.split('-')
                            start_int = self.ip_to_int(start_ip.strip())
                            end_int = self.ip_to_int(end_ip.strip())
                            if start_int and end_int:
                                ip_ranges.append((start_int, end_int))
                        elif self.is_ip_address(entry):
                            ip_int = self.ip_to_int(entry)
                            if ip_int:
                                ip_ranges.append((ip_int, ip_int))
                        else:
                            clean_entry = self.extract_domain_from_entry(entry)
                            if clean_entry:
                                non_ip_entries.append(clean_entry)
                    except Exception:
                        clean_entry = self.extract_domain_from_entry(entry)
                        if clean_entry:
                            non_ip_entries.append(clean_entry)
        
        selected_non_ip = []
        for entry in non_ip_entries:
            hash_val = self.hash_string(entry, seed)
            if (hash_val % shard_y) == (shard_x - 1):
                selected_non_ip.append(entry)
        
        work_chunks = []
        chunk_size = 25_000_000
        
        for start, end in ip_ranges:
            range_size = end - start + 1
            
            if range_size > chunk_size:
                current_start = start
                while current_start <= end:
                    chunk_end = min(current_start + chunk_size - 1, end)
                    work_chunks.append((current_start, chunk_end))
                    current_start = chunk_end + 1
            else:
                work_chunks.append((start, end))
        
        total_processed = len(non_ip_entries)
        total_excluded = 0
        all_selected = selected_non_ip.copy()
        completed_chunks = 0
        
        with ProcessPoolExecutor(max_workers=num_processes) as executor:
            future_to_chunk = {}
            for i, chunk in enumerate(work_chunks):
                future = executor.submit(
                    process_prefiltered_chunk_worker, 
                    chunk, blacklist_ranges, shard_x, shard_y, seed, i
                )
                future_to_chunk[future] = i
            
            for future in as_completed(future_to_chunk):
                chunk_id = future_to_chunk[future]
                try:
                    chunk_processed, chunk_excluded, chunk_selected = future.result()
                    total_processed += chunk_processed
                    total_excluded += chunk_excluded
                    all_selected.extend(chunk_selected)
                    completed_chunks += 1
                except Exception as exc:
                    console.print(f"Error in chunk {chunk_id}: {exc}")
        
        return total_processed, total_excluded, all_selected

    def count_total_items(self, file_path: str) -> int:
        """Quick count of total items (IPs + domains/URLs) for progress tracking"""
        total = 0
        
        if self.is_direct_input(file_path):
            entry = file_path.strip()
            try:
                if ':' in entry and '/' not in entry and '-' not in entry:
                    parts = entry.split(':')
                    if self.is_ip_address(parts[0]):
                        entry = parts[0]
                
                if '/' in entry and (self.is_ip_address(entry.split('/')[0]) or 
                    (entry.count('.') >= 3 and '-' not in entry)):
                    network = IPNetwork(entry)
                    total += int(network.last) - int(network.first) + 1
                elif '-' in entry and self.is_ip_address(entry.split('-')[0].strip()):
                    start_ip, end_ip = entry.split('-')
                    start_int = self.ip_to_int(start_ip.strip())
                    end_int = self.ip_to_int(end_ip.strip())
                    if start_int and end_int:
                        total += end_int - start_int + 1
                    else:
                        total += 1
                else:
                    total += 1
            except Exception:
                total += 1
        else:
            # Process as file
            with open(file_path, 'r') as f:
                for line in f:
                    entry = line.strip()
                    if not entry or entry.startswith("#"):
                        continue
                    try:
                        if ':' in entry and '/' not in entry and '-' not in entry:
                            parts = entry.split(':')
                            if self.is_ip_address(parts[0]):
                                entry = parts[0]
                        
                        if '/' in entry and (self.is_ip_address(entry.split('/')[0]) or 
                            (entry.count('.') >= 3 and '-' not in entry)):
                            network = IPNetwork(entry)
                            total += int(network.last) - int(network.first) + 1
                        elif '-' in entry and self.is_ip_address(entry.split('-')[0].strip()):
                            start_ip, end_ip = entry.split('-')
                            start_int = self.ip_to_int(start_ip.strip())
                            end_int = self.ip_to_int(end_ip.strip())
                            if start_int and end_int:
                                total += end_int - start_int + 1
                            else:
                                total += 1
                        else:
                            total += 1
                    except Exception:
                        total += 1
        return total

    def __call__(self, **kwargs):
        import sys

        shard = kwargs["shard"]
        seed = kwargs["seed"]
        input_file = kwargs["input_file"]
        exclude_file = kwargs.get("exclude_file")
        results_file = kwargs.get("results_file")

        try:
            x_str, y_str = shard.split("/")
            X = int(x_str)
            Y = int(y_str)
        except ValueError:
            error_console.print("[error] Invalid format for --shard. Use X/Y")
            return 1

        if Y < 1 or X < 1 or X > Y:
            error_console.print(f"[error] Invalid shard value: {X}/{Y}")
            return 1

        blacklist_ranges = []
        if exclude_file:
            try:
                blacklist_ranges = self.build_blacklist_ranges(exclude_file)
            except Exception as e:
                error_console.print(f"[error] Failed to load exclude list: {str(e)}")
                return 1

        total_items = self.count_total_items(input_file)
        
        # Always use all available CPU cores
        num_processes = mp.cpu_count()
        
        output_redirected = not sys.stdout.isatty()
        use_results_file = results_file is not None
        
        error_console.print(f"Processing {total_items:,} items")
        
        start_time = time.time()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Running..."),
            TimeElapsedColumn(),
            console=error_console,
            refresh_per_second=10
        ) as progress:
            task = progress.add_task("Processing...", total=None)
            total_processed, total_excluded, selected_items = self.read_file_addresses_ultra_parallel(
                input_file, blacklist_ranges, X, Y, seed, total_items
            )
        
        end_time = time.time()
        
        error_console.print(f"Completed in {end_time - start_time:.1f}s - Selected {len(selected_items):,} items - Excluded {total_excluded:,} IPs")
        
        included = total_processed - total_excluded

        if results_file:
            try:
                output_path = Path(results_file)
                extension = output_path.suffix.lower()
                if not extension:
                    output_path = Path(str(output_path) + '.txt')
                elif extension != '.txt':
                    error_console.print(f"[error] Unsupported file extension: {extension}. Only .txt format is supported.")
                    return 1

                os.makedirs(output_path.parent, exist_ok=True)
                
                with open(output_path, 'w') as f:
                    for addr in selected_items:
                        f.write(f"{addr}\n")
                error_console.print(f"Saved to {output_path}")
            except Exception as e:
                error_console.print(f"[error] Failed to write output file: {str(e)}")
                return 1
        else:
            
            for addr in selected_items:
                print(addr)
        
        return 0


def process_prefiltered_chunk_worker(chunk_range: tuple, blacklist_ranges: list, shard_x: int, shard_y: int, seed: int, chunk_id: int) -> tuple:
    """HARDCORE worker with exclude list pre-filtering - skip billions of excluded IPs"""
    cmd = ShardsCommand()
    
    range_start, range_end = chunk_range
    processed, excluded, selected = cmd.process_ip_range_pre_filtered(
        range_start, range_end, blacklist_ranges, shard_x, shard_y, seed
    )
    
    return processed, excluded, selected


def process_single_chunk_worker(chunk_range: tuple, blacklist_ranges: list, shard_x: int, shard_y: int, seed: int, chunk_id: int) -> tuple:
    """Worker function to process a single chunk"""
    cmd = ShardsCommand()
    
    range_start, range_end = chunk_range
    processed, excluded, selected = cmd.process_ip_range_ultra_vectorized(
        range_start, range_end, blacklist_ranges, shard_x, shard_y, seed
    )
    
    return processed, excluded, selected


def process_batch_worker(batch_ranges: list, blacklist_ranges: list, shard_x: int, shard_y: int, seed: int, batch_id: int) -> tuple:
    """Worker function to process a batch of IP ranges"""
    cmd = ShardsCommand()
    
    total_processed = 0
    total_excluded = 0
    all_selected = []
    
    for range_start, range_end in batch_ranges:
        processed, excluded, selected = cmd.process_ip_range_ultra_vectorized(
            range_start, range_end, blacklist_ranges, shard_x, shard_y, seed
        )
        total_processed += processed
        total_excluded += excluded
        all_selected.extend(selected)
    
    return total_processed, total_excluded, all_selected