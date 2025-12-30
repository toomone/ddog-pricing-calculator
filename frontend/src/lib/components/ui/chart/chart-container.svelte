<script lang="ts">
	import { cn } from "$lib/utils";
	import type { ChartConfig } from "./index.js";

	export let config: ChartConfig;
	let className: string | undefined = undefined;
	export { className as class };

	// Generate CSS variables from config
	$: cssVars = Object.entries(config).reduce((acc, [key, value]) => {
		if (value.color) {
			acc[`--color-${key}`] = value.color;
		}
		return acc;
	}, {} as Record<string, string>);

	$: style = Object.entries(cssVars)
		.map(([key, value]) => `${key}: ${value}`)
		.join("; ");
</script>

<div
	class={cn("flex aspect-square justify-center text-xs", className)}
	{style}
>
	<slot />
</div>

