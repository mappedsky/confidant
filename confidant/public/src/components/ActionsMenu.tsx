import React, { useState } from 'react';
import {
  IconButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Tooltip,
} from '@mui/material';
import MoreVertIcon from '@mui/icons-material/MoreVert';

export interface ActionsMenuItem {
  label: string;
  icon: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
  tooltip?: string;
  color?: 'inherit' | 'error';
}

interface ActionsMenuProps {
  label?: string;
  items: ActionsMenuItem[];
}

export default function ActionsMenu({
  label = 'More actions',
  items,
}: ActionsMenuProps) {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  const handleOpen = (event: React.MouseEvent<HTMLElement>) => {
    event.stopPropagation();
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => setAnchorEl(null);

  return (
    <>
      <Tooltip title={label}>
        <IconButton
          aria-label={label}
          size="small"
          onClick={handleOpen}
        >
          <MoreVertIcon fontSize="small" />
        </IconButton>
      </Tooltip>

      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleClose}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        transformOrigin={{ vertical: 'top', horizontal: 'right' }}
        slotProps={{ paper: { sx: { minWidth: 180 } } }}
      >
        {items.map((item) => {
          const menuItem = (
            <MenuItem
              key={item.label}
              onClick={() => {
                item.onClick();
                handleClose();
              }}
              disabled={item.disabled}
              sx={item.color === 'error' ? { color: 'error.main' } : undefined}
            >
              <ListItemIcon
                sx={item.color === 'error' ? { color: 'error.main' } : undefined}
              >
                {item.icon}
              </ListItemIcon>
              <ListItemText>{item.label}</ListItemText>
            </MenuItem>
          );

          if (!item.tooltip) {
            return menuItem;
          }

          return (
            <Tooltip key={item.label} title={item.tooltip} placement="left">
              <span>{menuItem}</span>
            </Tooltip>
          );
        })}
      </Menu>
    </>
  );
}
