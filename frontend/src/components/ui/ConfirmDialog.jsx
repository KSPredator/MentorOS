import React from 'react';
import { AlertTriangle } from 'lucide-react';
import Modal from './Modal';
import Button from './Button';

/** Destructive confirmation dialog bound to useUI.confirmState. */
export default function ConfirmDialog({ state, onClose }) {
  if (!state) return null;
  return (
    <Modal open onClose={onClose} title={state.title} maxWidth="max-w-md">
          <div className="flex gap-3">
            <div className="w-10 h-10 rounded-xl bg-dangerSoft text-danger flex items-center justify-center flex-shrink-0">
              <AlertTriangle size={18} />
            </div>
            <p className="text-sm text-textMuted leading-relaxed pt-1.5">{state.message}</p>
          </div>
          <div className="flex justify-end gap-2 mt-5">
            <Button variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={() => {
                state.onConfirm?.();
                onClose();
              }}
            >
              {state.confirmLabel || 'Delete'}
            </Button>
</div>
    </Modal>
  );
}
