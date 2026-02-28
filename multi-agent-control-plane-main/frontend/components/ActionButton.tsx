type ActionButtonProps = {
  label: string;
};

export function ActionButton({ label }: ActionButtonProps) {
  return (
    <button
      type="button"
      className="rounded-full bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-blue-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
    >
      {label}
    </button>
  );
}
