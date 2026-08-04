export function PageHeader({ title, description }: { title: string; description?: string }) {
  return (
    <div className="mb-6 flex gap-3">
      <span className="mt-1 h-7 w-[3px] shrink-0 rounded-full bg-secondary" aria-hidden="true" />
      <div>
        <h1 className="text-[26px] font-semibold leading-tight text-foreground sm:text-[28px]">{title}</h1>
        {description && <p className="mt-1.5 text-sm text-muted-foreground">{description}</p>}
      </div>
    </div>
  );
}
