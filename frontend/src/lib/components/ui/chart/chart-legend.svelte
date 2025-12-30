<script lang="ts">
	import { cn } from "$lib/utils";

	interface LegendItem {
		name: string;
		color: string;
		value?: string | number;
		percentage?: number;
	}

	export let items: LegendItem[] = [];
	export let orientation: "horizontal" | "vertical" = "vertical";
	let className: string | undefined = undefined;
	export { className as class };
</script>

<div
	class={cn(
		"flex gap-3 text-sm",
		orientation === "vertical" ? "flex-col" : "flex-row flex-wrap",
		className
	)}
>
	{#each items as item}
		<div class="flex items-center gap-2">
			<div
				class="h-3 w-3 rounded-sm shrink-0"
				style="background-color: {item.color}"
			></div>
			<span class="text-muted-foreground">{item.name}</span>
			{#if item.percentage !== undefined}
				<span class="font-medium">{item.percentage.toFixed(1)}%</span>
			{/if}
			{#if item.value !== undefined}
				<span class="text-muted-foreground text-xs">({item.value})</span>
			{/if}
		</div>
	{/each}
</div>

