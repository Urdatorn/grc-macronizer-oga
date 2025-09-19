#!/bin/bash
# clear_diagnostics.sh
# Safely remove diagnostic files without hitting "Argument list too long"

# Remove macronizer* files
find diagnostics/logs/ -type f -name "macronizer*" -delete

# Remove still_ambiguous* files
find diagnostics/still_ambiguous/ -type f -name "still_ambiguous*" -delete

# Remove files ending with % in modules
find diagnostics/modules/ -type f -name "*" -delete

echo "Diagnostics cleared successfully."
