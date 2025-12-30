<script lang="ts">
	import { cn } from "$lib/utils";

	let className: string | undefined = undefined;
	export { className as class };
	export let value: string = "";
</script>

<textarea
	class={cn(
		"border-input placeholder:text-muted-foreground focus-visible:ring-ring flex min-h-[60px] w-full rounded-md border bg-transparent px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 disabled:cursor-not-allowed disabled:opacity-50",
		className
	)}
	bind:value
	{...$$restProps}
>
</textarea>

