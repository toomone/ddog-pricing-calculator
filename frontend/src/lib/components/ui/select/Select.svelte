<script lang="ts">
	import { cn } from '$lib/utils';

	let className: string | undefined = undefined;
	export { className as class };
	export let value: string = '';
	export let disabled: boolean = false;
</script>

<select
	{disabled}
	bind:value
	class={cn(
		'flex h-10 w-full items-center justify-between rounded-lg border-2 border-input bg-background px-3 py-2 text-sm ring-offset-background',
		'placeholder:text-muted-foreground',
		'focus:outline-none focus:ring-2 focus:ring-datadog-purple focus:ring-offset-2 focus:border-datadog-purple',
		'disabled:cursor-not-allowed disabled:opacity-50',
		'transition-all duration-200',
		'cursor-pointer appearance-none',
		className
	)}
	on:change
	{...$$restProps}
>
	<slot />
</select>

