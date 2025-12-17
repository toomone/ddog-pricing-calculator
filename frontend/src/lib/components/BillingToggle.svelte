<script lang="ts">
	import { cn } from '$lib/utils';
	import { createEventDispatcher } from 'svelte';

	export let value: 'annually' | 'monthly' | 'on_demand' = 'annually';

	const dispatch = createEventDispatcher<{ change: 'annually' | 'monthly' | 'on_demand' }>();

	const options = [
		{ value: 'annually', label: 'Annual', savings: 'Save ~17%' },
		{ value: 'monthly', label: 'Monthly', savings: null },
		{ value: 'on_demand', label: 'On-Demand', savings: null }
	] as const;

	function handleSelect(newValue: 'annually' | 'monthly' | 'on_demand') {
		value = newValue;
		dispatch('change', value);
	}
</script>

<div class="inline-flex rounded-xl bg-muted/50 p-1.5 backdrop-blur-sm">
	{#each options as option}
		<button
			type="button"
			class={cn(
				'relative rounded-lg px-4 py-2 text-sm font-medium transition-all duration-200',
				value === option.value
					? 'bg-datadog-purple text-white shadow-lg shadow-datadog-purple/25'
					: 'text-muted-foreground hover:text-foreground'
			)}
			on:click={() => handleSelect(option.value)}
		>
			<span class="relative z-10">{option.label}</span>
			{#if option.savings && value === option.value}
				<span
					class="absolute -top-2 right-0 translate-x-1/4 rounded-full bg-datadog-green px-2 py-0.5 text-[10px] font-bold text-white"
				>
					{option.savings}
				</span>
			{/if}
		</button>
	{/each}
</div>

