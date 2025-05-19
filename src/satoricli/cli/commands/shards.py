import random
import os
from argparse import ArgumentParser
from typing import Optional, List
from pathlib import Path

from satoricli.cli.commands.base import BaseCommand
from satoricli.cli.utils import console, error_console


class ShardsCommand(BaseCommand):
    
    name = "shards"
    
    def register_args(self, parser: ArgumentParser):
        
        parser.add_argument("--shard", required=True, help="Current shard and total (X/Y format)")
        parser.add_argument("--seed", type=int, required=True, help="Seed for pseudorandom permutation")
        parser.add_argument("--input", dest="input_file", required=True,help="Input file with addresses (any path)")
        parser.add_argument("--blacklist", dest="blacklist_file", help="File with addresses to exclude (any path)")
        parser.add_argument("--results", dest="results_file", help="Save results to text file (must have .txt extension or no extension; default is .txt)")
    
    def read_file_addresses(self, file_path: str) -> List[str]:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        try:
            with open(file_path, 'r') as f:
                return [line.strip() for line in f if line.strip()]
        except Exception as e:
            raise ValueError(f"Error reading {file_path}: {str(e)}")
            
    def __call__(self, shard: str, seed: int, input_file: str, 
                blacklist_file: Optional[str] = None, results_file: Optional[str] = None, **kwargs):
        
        # Parse the X/Y shard format
        try:
            x_str, y_str = shard.split("/")
            X = int(x_str)
            Y = int(y_str)
        except ValueError:
            error_console.print("[error]ERROR:[/] Invalid format for --shard. Use X/Y")
            return 1
        
        # Validate X and Y values
        if Y < 1 or X < 1 or X > Y:
            error_console.print(f"[error]ERROR:[/] Invalid shard value: {X}/{Y}")
            return 1
        
        # Read input file
        try:
            addresses = self.read_file_addresses(input_file)
            if not addresses:
                error_console.print(f"[error]ERROR:[/] No valid addresses found in: {input_file}")
                return 1
        except FileNotFoundError:
            error_console.print(f"[error]ERROR:[/] Input file not found: {input_file}")
            return 1
        except ValueError as e:
            error_console.print(f"[error]ERROR:[/] {str(e)}")
            return 1
        
        # Apply blacklist if provided
        blacklist_set = set()
        if blacklist_file:
            try:
                blacklist_addresses = self.read_file_addresses(blacklist_file)
                for addr in blacklist_addresses:
                    blacklist_set.add(addr)
                    # If the address is just an IP (without port), 
                    # add it as base for comparison
                    if ":" not in addr:
                        blacklist_set.add(addr + ":")
            except FileNotFoundError:
                error_console.print(f"[error]ERROR:[/] Blacklist file not found: {blacklist_file}")
                return 1
            except ValueError as e:
                error_console.print(f"[error]ERROR:[/] Error in blacklist file: {str(e)}")
                return 1
        
        # Filter addresses using the blacklist
        filtered_addresses = []
        for addr in addresses:
            # Check if the exact address is in the blacklist
            if addr in blacklist_set:
                continue
                
            # Check if the IP base (without port) is in the blacklist
            ip_part = addr.split(":")[0] if ":" in addr else addr
            if ip_part + ":" in blacklist_set:
                continue
                
            # If it passes both checks, include it
            filtered_addresses.append(addr)
        
        # Randomly permute with fixed seed
        rnd = random.Random(seed)
        rnd.shuffle(filtered_addresses)
        
        # Select elements for shard X
        shard_addresses = [addr for index, addr in enumerate(filtered_addresses) if index % Y == (X-1)]
        
        # Output handling: print to file or stdout
        if results_file:
            try:
                output_path = Path(results_file)
                
                # Check the file extension - only .txt is supported
                extension = output_path.suffix.lower()
                
                # If no extension provided, add .txt
                if not extension:
                    output_path = Path(str(output_path) + '.txt')
                    console.print(f"No extension provided, using: {output_path}")
                # If extension is not .txt, show error
                elif extension != '.txt':
                    error_console.print(f"[error]ERROR:[/] Unsupported file extension: {extension}. Only .txt format is supported.")
                    return 1
                
                # Create directory if it doesn't exist
                os.makedirs(output_path.parent, exist_ok=True)
                
                # Write addresses to file (one per line)
                with open(output_path, 'w') as f:
                    for addr in shard_addresses:
                        f.write(f"{addr}\n")
                
                console.print(f"Results saved to {output_path}")
            except Exception as e:
                error_console.print(f"[error]ERROR:[/] Failed to write to output file: {str(e)}")
                return 1
        else:
            # Print results to stdout
            for addr in shard_addresses:
                console.print(addr)
            
        # Return success
        return 0