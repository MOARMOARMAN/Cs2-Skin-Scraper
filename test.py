class Solution:
    def searchInsert(self, nums: List[int], target: int) -> int:
        left = 0
        right = len(nums) - 1
        while left <= right:
            mid = (left + right) // 2
            if nums[mid] == target:
                return mid 
            elif nums[mid] < target:
                left = mid + 1
            else:
                right = mid - 1
        return left

MySolution = Solution()
nums: List[int] = [1, 3, 4, 6, 7, 8, 9, 10]
print(MySolution.searchInsert(nums, 11))